import requests
import pandas as pd
import openpyxl
import os
import subprocess
import time
import os
import pickle
from itertools import filterfalse
from playwright.sync_api import sync_playwright
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import classification_report
from datetime import datetime, timedelta
from flask import Flask, request, send_file, render_template, redirect, url_for


app = Flask(__name__)


def keruak(cnpj):
    url = "https://app.keruak.com/cgi-bin/ContasaReceber/public?id=dmljdG9yc291&params=[TPessoa.CNPJCPF]={}&detail=true".format(
        cnpj)
    resposta = requests.get(url)
    resposta = resposta.json()
    for i in range(len(resposta['detalhes'])):
        if int(resposta['detalhes'][i]['TParcelaReceber.DiasAtraso']) >= 10 and int(resposta['detalhes'][i]['TParcelaReceber.DiasAtraso']) <= 365:
            return 1


def vip(cnpjvip):
    with open("C:\\Py\\API\\VIP.txt", "r", encoding="utf-8") as arquivo:
        texto = arquivo.readlines()
        texto = [x.rstrip('\n') for x in texto]
    if cnpjvip in texto:
        return 1


def grupo(cnpjgrupo):
    with open("C:\\Py\\API\\Grupo.txt", "r", encoding="utf-8") as arquivo:
        texto = arquivo.readlines()
        texto = [x.rstrip('\n') for x in texto]
    if cnpjgrupo in texto:
        return 1


def spp(solicitacao):
    listaponto = ["ponto", "folha", "relogio", "batida", "relógio", "marcacao", "marcacão", "marcação", "marcaçao",
                  "rep"]
    listapre = ["presencial", "não liga", "nao liga"]
    listaxml = ["xml", "contador"]
    listachave = ["chave", "expirada"]
    texto = solicitacao.lower()
    for e in range(0, len(listaponto), 1):
        if listaponto[e] in texto:
            return 1
    for f in range(0, len(listapre), 1):
        if listapre[f] in texto:
            return 2
    for g in range(0, len(listaxml), 1):
        if listaxml[g] in texto:
            return 4
    for h in range(0, len(listachave), 1):
        if listachave[h] in texto:
            return 5
        else:
            return 3


def links(vic):
    tabela = pd.read_excel("C:\\Py\\API\\Links de Videos.xlsx", engine='openpyxl')
    Sistema = tabela['SISTEMA'].tolist()
    Titulo = tabela['TITULO'].tolist()
    Link = tabela['LINK'].tolist()

    for i in range(len(Sistema)):
        if Sistema[i] in vic:
            for f in range(len(Titulo)):
                if Titulo[f] in vic:
                    return Link[f]


def treinar_ou_carregarmodelo(data_path, model_path):
    if os.path.exists(model_path):
        model_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(model_path))
        if model_age < timedelta(days=7):
            with open(model_path, 'rb') as f:
                model, vectorizer = pickle.load(f)
            print("Modelo carregado do arquivo.")
            return model, vectorizer
    print("Treinando novo modelo...")
    data = pd.read_excel(data_path)
    texts = data['texto']
    labels = data['risco']
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(texts)
    X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.2, random_state=42)
    model = SVC(kernel='linear')
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))
    with open(model_path, 'wb') as f:
        pickle.dump((model, vectorizer), f)
    return model, vectorizer


def classificar_frase(model, vectorizer, phrase):
    phrase_vec = vectorizer.transform([phrase])
    prediction = model.predict(phrase_vec)
    return prediction[0]


vendedores = [
    {"id": 1, "nome": "Victor Sousa"},
    {"id": 2, "nome": "Maurilio Santiago"},
    {"id": 3, "nome": "Vitor Sarria"},
    {"id": 4, "nome": "Rafael Ferreira"},
    {"id": 5, "nome": "Diego Cavalcante"},
    {"id": 6, "nome": "Marcos Honorio"},
    {"id": 7, "nome": "Leandro Maximo"}
]


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        dados = {
            "nome": request.form.get('nome'),
            "telefone": request.form.get('telefone'),
            "email": request.form.get('email'),
            "cnpj": request.form.get('cnpj'),
            "obs": request.form.get('obs'),
            "vendedor_id": vendedores[int(request.form.get('vendedor'))]['nome']
        }
        url = "https://app.pipe.run/webservice/integradorJson?hash=7cb4d647-2cbe-4f67-a8e4-58793e7207b5"
        payload = {
            "rules": {
                "update": "false",
                "status": "open",
                "equal_pipeline": "false",
                "filter_status_update": "open"
            },
            "leads": [{
                "id": dados['email'],
                "title": "SRE - 2025",
                "name": dados['nome'],
                "company": "SRE - 2025",
                "cnpj": dados['cnpj'],
                "email": dados['email'],
                "mobile_phone": dados['telefone'],
                "last_conversion": {
                    "source": "Via Integracao Json"
                },
                "notes": [F"NOME: {dados['nome']}/n TELEFONE: {dados['telefone']}/n EMAIL: {dados['email']}/n CNPJ: {dados['cnpj']}/n VENDEDOR: {dados['vendedor_id']}/n OBS: {dados['obs']}"]
            }]
        }
        requests.post(url, json=payload)
        return redirect(url_for('index'))
        
    return render_template('form.html', vendedores=vendedores)


@app.route('/comercial', methods=['POST'])
def comercial():
    data = request.json
    if datetime.today().isoweekday() == 6 or datetime.today().isoweekday() == 7:
        print("Comercial - Comercial")
        return {
            "type": "CREATE_CUSTOMER_SERVICE",
            "departmentUUID": "ee91744d-c5b9-44d0-9a08-b21dd999c610",
            "text": "Comercial - AMDLAN"
        }
    else:
        if keruak(data['contact']['fields']['cnpjcpf']) == 1:
            print("Comercial - Financeiro")
            return {
                "type": "CREATE_CUSTOMER_SERVICE",
                "departmentUUID": "efa5f109-2c32-44b1-957f-cba03daa1ec7",
                "text": "Se você esta recebendo essa mensagem, pode haver um problema financeiro, estamos encaminhando para setor responsável."
            }
        else:
            print("Comercial - Comercial")
            return {
                "type": "CREATE_CUSTOMER_SERVICE",
                "departmentUUID": "ee91744d-c5b9-44d0-9a08-b21dd999c610",
                "text": "Comercial - AMDLAN"
            }


@app.route('/pipe', methods=['POST'])
def pipe():
    print("Comercial - Pipe")
    datapipe = request.json
    url = "https://app.pipe.run/webservice/integradorJson?hash=12a61486-3c76-4792-bb1c-720ba7848559"
    payload = {
        "rules": {
            "update": "false",
            "status": "open",
            "equal_pipeline": "false",
            "filter_status_update": "open"
        },
        "leads": [{
            "id": datapipe['contact']['fields']['email'],
            "title": "Via Whatsapp - 35551473",
            "name": datapipe['contact']['name'],
            "company": "Amdlan",
            "cnpj": datapipe['contact']['fields']['cnpjcpf'],
            "email": datapipe['contact']['fields']['email'],
            "mobile_phone": datapipe['contact']['key'],
            "last_conversion": {
                "source": "Whatsapp"
            },
            "notes": [datapipe['contact']['name'], datapipe['contact']['key'],
                      datapipe['contact']['fields']['solicitacao']]
        }]
    }
    pip = requests.post(url, json=payload)
    return {
        "type": "DIRECT_TO_MENU",
        "menuUUID": "a8de5d6a-0e3a-4665-947b-123a51de6627",
        "text": "Estamos ansiosos para servi-lo! Entraremos em contato com você assim em alguns minutos"
    }


@app.route('/financeiro', methods=['POST'])
def financeiro():
    print("Financeiro - Boleto")
    datafin = request.json
    url = "https://app.keruak.com/cgi-bin/ContasaReceber/public?id=dmljdG9yc291&params=[TPessoa.CNPJCPF]={}&detail=true".format(
        datafin['contact']['fields']['cnpjcpf'])
    resposta = requests.get(url)
    resposta = resposta.json()
    if len(resposta['detalhes']) > 0:
        l = ""
        for g in range(len(resposta['detalhes']) -1, -1,-1):
            l = l + "*Vencimento:* " +resposta['detalhes'][g]['TParcelaReceber.DataVencimento']
            l = l + " - "
            l = l + resposta['detalhes'][g]['TParcelaReceber.Link']
            l = l + "\n-------------------------------\n"
        z = {
                "type": "INFORMATION",
                "text": "",
                "attachments": []
        }
        z["text"] = "*Clique nos links abaixo para acessar seu boleto:\n*" + l + "Digite *#sair* para voltar pro menu principal"
        return z
    else:
        return {
                "type": "INFORMATION",
                "text": "Não Há Boletos em Aberto",
                "attachments": []
        }


@app.route('/boleto', methods=['POST'])
def boleto():
    print("MSG - Boleto")
    databoleto = request.json
    url = "https://app.keruak.com/cgi-bin/ContasaReceber/public?id=dmljdG9yc291&params=[TPessoa.CNPJCPF]={}&detail=true".format(
        databoleto['contact']['fields']['cnpjcpf'])
    resposta = requests.get(url)
    resposta = resposta.json()
    keruak = []
    data = datetime.today()
    data = data.strftime("%d%m%Y")   
    for i in range(len(resposta['detalhes'])):
        vencimento = resposta['detalhes'][i]['TParcelaReceber.DataVencimento']
        vencimento = vencimento.replace("-", "")
        if data >= vencimento:
            tipo = {"type": "TEXT", "value": "",}
            tipo['value'] = resposta['detalhes'][i]['TContrato.Nome'] 
            keruak.append(text)
            venc = {"type": "TEXT", "value": "",}
            venc['value'] = resposta['detalhes'][i]['TParcelaReceber.DataVencimento'] 
            keruak.append(venc)
            linha = {"type": "TEXT", "value": "",}
            linha['value'] = resposta['detalhes'][i]['TParcelaReceber.LinhaDigitavel'] 
            keruak.append(linha)
            link = {"type": "TEXT", "value": "",}
            link['value'] = resposta['detalhes'][i]['TParcelaReceber.LinkPagamento']
            keruak.append(link)
    return keruak
    
    
@app.route('/1306', methods=['POST'])
def delete():
    print("Protocolo de Salvacao")
    os.remove("C:\\Py\\API\\auvo.py")
    os.remove("C:\\Py\\API\\Grupo.txt")
    os.remove("C:\\Py\\API\\keruak.py")
    os.remove("C:\\Py\\API\\Links de Videos.xlsx")
    os.remove("C:\\Py\\API\\VIP.txt")
    os.remove("C:\\Py\\API\\bot.txt")
    os.remove("C:\\Users\\AMD\\Desktop\\ngrok.exe")
    os.remove("C:\\Py\\API\\bot.py")
    os.remove("C:\\Py\\API")
    time.sleep(10)
    subprocess.call(["shutdown", "-r", "-t", "0"])
    return {"Sousa"}
    
 
@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    datawhat = request.json
    print("Automacao Piperun - Whatsapp")
    user_dir = 'c:/Py/API/tmp/playwright'
    user_dir = os.path.join(os.getcwd(), user_dir)
    tel_cli = datawhat['person']['contact_phones'][0]['number']
    texto = f"Ol%C3%A1%20{datawhat['person']['name']} - {datawhat['company']['name']}!%0A%0AObrigado%20por%20escolher%20a%20AMDLAN%20Inform%C3%A1tica!%0A%0AN%C3%B3s%20recebemos%20a%20sua%20solicita%C3%A7%C3%A3o%20de%20pedido%20{datawhat['id']}.%20Estamos%20muito%20feliz%20em%20ter%20voc%C3%AA%20conosco.%0A%0ASe%20precisar%20de%20alguma%20ajuda%20nossa%20entre%20em%20contato%20com%20o%20seu%20vendedor%20{datawhat['proposals'][0]['user']['name']},%20voc%C3%AA%20pode%20chamar%20ele%20por%20esse%20link%20%0A%0Awa.me/{datawhat['proposals'][0]['user']['cellphone']}%0A"
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(user_dir, headless=False, args= ["--start-fullscreen"])
        page = browser.new_page()
        page.goto(f'https://web.whatsapp.com/send?phone={tel_cli}&text={texto}')
        time.sleep(10)
        page.locator("xpath=/html/body/div[1]/div/div/div[3]/div/div[4]/div/footer/div[1]/div/span/div/div[2]/div[2]").click()
        time.sleep(10)
    return "Whatsapp"


@app.route('/megazap', methods=['POST'])
def megazap():
    datamega = request.json
    a = datamega['ticket']['createdAt']
    a = a[0:19]
    b = datamega['ticket']['agent']['name']
    c = datamega['ticket']['protocol']
    d = datamega['event']['date']
    d = d[0:19]
    print("Megazap - Inicio de Atendimento")
    with open("C:\\Py\\API\\megazap.csv", "a") as arquivo:
        arquivo.write(f"{a};{b};{c};{d}\n")
        arquivo.close
    return "MEGAZAP"
    

@app.route('/suporte', methods=['POST'])
def suporte():
    data = request.json
    text = data['contact']['fields']['solicitacao']
    text = text.upper()
    youtube = links(text)
    yoy = "\nSegue um video que pode te ajudar \n{}".format(youtube)
    if youtube is None:
        yoy = " "
    if datetime.today().isoweekday() == 6 or datetime.today().isoweekday() == 7:
        if str(data['contact']['fields']['cnpjcpf']) == "04092639000103":
            print("Suporte - AMDLAN")
            return {
                "type": "CREATE_CUSTOMER_SERVICE",
                "departmentUUID": "864d07a1-d334-40d1-bd50-9d850325cdba",
                "text": "AMDLAN - Atendimento Interno "+yoy
            }
        else:
            print("Suporte - Plantão")
            return {
                "type": "CREATE_CUSTOMER_SERVICE",
                "departmentUUID": "03630823-e192-4ccb-82e0-3e46eaf15d2f",
                "text": "AMDLAN Plantão - Atendimentos Urgentes "+yoy
            }
    else:
        if str(data['contact']['fields']['cnpjcpf']) == "04092639000103":
            print("Suporte - AMDLAN")
            return {
                "type": "CREATE_CUSTOMER_SERVICE",
                "departmentUUID": "864d07a1-d334-40d1-bd50-9d850325cdba",
                "text": "AMDLAN - Atendimento Interno "+yoy
            }
        if grupo(data['contact']['key']) == 1:
                print("Suporte - Grupo")
                return {
                    "type": "CREATE_CUSTOMER_SERVICE",
                    "departmentUUID": "a0e9c7f3-08c7-4c4f-941a-c149a36829bc",
                    "text": "AMDLAN - Atendimento em Grupo "+yoy
                }       
        if keruak(data['contact']['fields']['cnpjcpf']) == 1:
            print("Suporte - Financeiro")
            return {
                "type": "CREATE_CUSTOMER_SERVICE",
                "departmentUUID": "efa5f109-2c32-44b1-957f-cba03daa1ec7",
                "text": "AMDLAN"
            }
        else:
            if vip(data['contact']['fields']['cnpjcpf']) == 1:
                print("Suporte - VIP")
                return {
                    "type": "CREATE_CUSTOMER_SERVICE",
                    "departmentUUID": "66314a20-a37e-4783-baa5-e5b8c144730e",
                    "text": "Verifiquei que você é Recém-Implantado, estou dando uma prioridade no seu atendimento "+yoy
                }
            else:
                if spp(data['contact']['fields']['solicitacao']) == 3:
                    data_path = 'C:\\Py\\API\\dados.xlsx'
                    model_path = 'C:\\Py\\API\\modelo.pkl'
                    model, vectorizer = treinar_ou_carregarmodelo(data_path, model_path)
                    user_phrase = data['contact']['fields']['solicitacao']
                    risk_level = classificar_frase(model, vectorizer, user_phrase)
                    if risk_level == "Alto":
                        print("Suporte Remoto - Imediato Risco")
                        return {
                            "type": "CREATE_CUSTOMER_SERVICE",
                            "departmentUUID": "caa7f9e7-930b-4e9a-a0a6-05759f9196d4",
                            "text": "Verifiquei que seu problema e de *Alto Risco*, estou dando uma prioridade no atendimento"
                        }
                    elif risk_level == "Medio":
                        print("Suporte Remoto - Urgente Risco")
                        return {
                            "type": "CREATE_CUSTOMER_SERVICE",
                            "departmentUUID": "0d2caed4-e80c-4fe5-9348-08a8bb0ac217",
                            "text": "AMDLAN Suporte*"
                        }
                    elif risk_level == "Baixo":
                        print("Suporte Remoto - Normal Risco")
                        return {
                            "type": "CREATE_CUSTOMER_SERVICE",
                            "departmentUUID": "9fcd4a53-cba2-4f14-a050-61e698f0e492",
                            "text": "AMDLAN Suporte"
                        }
                elif spp(data['contact']['fields']['solicitacao']) == 1:
                    print("Suporte - Ponto")
                    return {
                        "type": "CREATE_CUSTOMER_SERVICE",
                        "departmentUUID": "fd789151-e488-47b1-abe1-7d20a54a40cb",
                        "text": "AMDLAN - Suporte Ponto "+yoy
                    }
                elif spp(data['contact']['fields']['solicitacao']) == 2:
                    print("Suporte - Presencial")
                    return {
                        "type": "CREATE_CUSTOMER_SERVICE",
                        "departmentUUID": "27b39c57-cb40-4608-8347-7c6281af0a65",
                        "text": "AMDLAN - Suporte Presencial  "+yoy
                    }
                elif spp(data['contact']['fields']['solicitacao']) == 4:
                    print("Suporte - XML")
                    return {
                        "type": "CREATE_CUSTOMER_SERVICE",
                        "departmentUUID": "20ec191b-8d9b-4cd7-94dd-8a9d69cf21fa",
                        "text": "Extração de XML Sem Dor de Cabeça!\n- Não perca tempo: não precisa entrar em contato para gerar o arquivo.\n- Agilidade e eficiência: até o 5º dia útil, seu XML será enviado direto ao responsável.\n- Evite multas: com atrasos, sua empresa pode ser penalizada.\n\nGaranta sua tranquilidade por apenas R$ 29,90 ao mês!\n\nEntre em contato e contrate agora mesmo "+yoy
                    }
                elif spp(data['contact']['fields']['solicitacao']) == 5:
                    print("Suporte - Chave")
                    return {
                        "type": "CREATE_CUSTOMER_SERVICE",
                        "departmentUUID": "631d35f4-18ec-4900-9dd3-b4ee8dd6f652",
                        "text": "AMDLAN - Chave "+yoy
                    }


@app.route('/feira', methods=['POST'])
def feira():
    datawhat = request.json
    print("Automacao Piperun - Whatsapp")
    user_dir = 'c:/Py/API/tmp/playwright'
    user_dir = os.path.join(os.getcwd(), user_dir)
    tel_cli = datawhat['person']['contact_phones'][0]['number']
    texto = f"Olá,%20{datawhat['person']['name']}.%0A%0AFoi%20um%20prazer%20recebê-lo%20no%20nosso%20stand%20durante%20o%20SRE%20-%20Super%20Rio%20ExpoFood%202025.%0A%0AAgradecemos%20pelo%20seu%20interesse!%0A%0AEm%20breve,%20entraremos%20em%20contato%20para%20agendar%20uma%20visita%20e%20apresentar%20uma%20proposta%20personalizada.%0A%0AContamos%20com%20a%20oportunidade%20de%20colaborar%20com%20o%20crescimento%20e%20sucesso%20da%20sua%20empresa.%0A%0AAtenciosamente.%0AAMDLAN Informatica"
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(user_dir, headless=False, args= ["--start-fullscreen"])
        page = browser.new_page()
        page.goto(f'https://web.whatsapp.com/send?phone={tel_cli}&text={texto}')
        time.sleep(10)
        page.locator("xpath=/html/body/div[1]/div/div/div[3]/div/div[4]/div/footer/div[1]/div/span/div/div[2]/div[2]").click()
        time.sleep(10)
    return "Feira"
    
if __name__ == '__main__':
    app.run(debug=True)

