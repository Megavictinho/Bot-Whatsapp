import os
import pickle
from datetime import datetime, timedelta
import pandas as pd
import requests
from flask import Flask, render_template, request, redirect, send_from_directory, url_for
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
import re

app = Flask(__name__)
vip_dados = 'vip_dados.xlsx'
arquivo_texto = 'dados.xlsx'
arquivo_feriados = 'feriados.txt'
ARQUIVO = 'links de videos.xlsx'

def keruak(cnpj):
    url = "https://app.keruak.com/cgi-bin/ContasaReceber/public?id=dmljdG9yc291&params=[TPessoa.CNPJCPF]={}&detail=true".format(
        cnpj)
    resposta = requests.get(url)
    resposta = resposta.json()
    for i in range(len(resposta['detalhes'])):
        if int(resposta['detalhes'][i]['TParcelaReceber.DiasAtraso']) >= 10:
            if int(resposta['detalhes'][i]['TParcelaReceber.DiasAtraso']) <= 1095:
                return 1

def vip(cnpjvip):
    tabela = pd.read_excel(vip_dados, engine='openpyxl')
    sistema = tabela['cnpj'].tolist()
    if cnpjvip in sistema:
        return 1

def grupo(cnpjgrupo):
    with open("//home//flask_app/grupo.txt", "r", encoding="utf-8") as arquivo:
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
    tabela = pd.read_excel("//home/flask_app//links de videos.xlsx", engine='openpyxl')
    sistema = tabela['SISTEMA'].tolist()
    titulo = tabela['TITULO'].tolist()
    link = tabela['LINK'].tolist()

    for i in range(len(sistema)):
        if sistema[i] in vic:
            for f in range(len(titulo)):
                if titulo[f] in vic:
                    return link[f]

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
    x = vectorizer.fit_transform(texts)
    x_train, x_test, y_train, y_test = train_test_split(x, labels, test_size=0.2, random_state=42)
    model = SVC(kernel='linear')
    model.fit(x_train, y_train)
    y_pred = model.predict(x_test)
    print(classification_report(y_test, y_pred))
    with open(model_path, 'wb') as f:
        pickle.dump((model, vectorizer), f)
    return model, vectorizer

def classificar_frase(model, vectorizer, phrase):
    phrase_vec = vectorizer.transform([phrase])
    prediction = model.predict(phrase_vec)
    return prediction[0]

def carregar_feriados():
    if not os.path.exists(arquivo_feriados):
        return []
    with open(arquivo_feriados, 'r', encoding='utf-8') as f:
        return [linha.strip() for linha in f if linha.strip()]

def salvar_feriado(data):
    with open(arquivo_feriados, 'a', encoding='utf-8') as f:
        f.write(f"{data}\n")

def formatar_numero(numero):
    numero_limpo = re.sub(r'\D', '', numero)
    if numero_limpo.startswith('55'):
        return numero_limpo
    else:
        return '55' + numero_limpo


@app.route('/', methods=['GET'])
def main():
    return  render_template('index.html')

@app.route('/amdlanvip', methods=['GET', 'POST'])
def vip():
    if request.method == 'POST':
        nome = request.form.get('nome')
        cnpj = request.form.get('cnpj')
        data = request.form.get('data')
        if nome and cnpj and data:
            df = pd.read_excel(vip_dados)
            novo_registro = pd.DataFrame({'nome': [nome], 'cnpj': [cnpj], 'data': [data]})
            df = pd.concat([df, novo_registro], ignore_index=True)
            df.to_excel(vip_dados, index=False)
        return redirect('/amdlanvip')
    df = pd.read_excel(vip_dados)
    hoje = datetime.today().date()
    df['dias_desde_data'] = df['data'].apply(lambda d: (hoje - pd.to_datetime(d).date()).days)
    registros = df.to_dict(orient='records')
    print(registros)
    return render_template('vip.html', registros=registros)

@app.route('/delete/<int:index>')
def delete(index):
    df = pd.read_excel(vip_dados)
    if 0 <= index < len(df):
        df = df.drop(index)
        df.reset_index(drop=True, inplace=True)
        df.to_excel(vip_dados, index=False)
    return redirect('/amdlanvip')

@app.route('/amdlanvideos', methods=['GET', 'POST'])
def videos():
    if request.method == 'POST':
        sistema = request.form['sistema']
        titulo = request.form['titulo']
        link = request.form['link']

        novo_dado = pd.DataFrame([[sistema, titulo, link]], columns=['SISTEMA', 'TITULO', 'LINK'])

        if os.path.exists(ARQUIVO):
            dados_existentes = pd.read_excel(ARQUIVO)
            dados_atualizados = pd.concat([dados_existentes, novo_dado], ignore_index=True)
        else:
            dados_atualizados = novo_dado

        with pd.ExcelWriter(ARQUIVO, engine='openpyxl', mode='w') as writer:
            dados_atualizados.to_excel(writer, index=False)

        return redirect('/amdlanvideos')

    if os.path.exists(ARQUIVO):
        dados = pd.read_excel(ARQUIVO)
        dados['INDEX'] = dados.index
    else:
        dados = pd.DataFrame(columns=['SISTEMA', 'TITULO', 'LINK', 'INDEX'])

    return render_template('videos.html', dados=dados.to_dict(orient='records'))

@app.route('/amdlanvideos/apagar/<int:index>')
def apagar(index):
    if os.path.exists(ARQUIVO):
        dados = pd.read_excel(ARQUIVO)
        if 0 <= index < len(dados):
            dados = dados.drop(index).reset_index(drop=True)
            with pd.ExcelWriter(ARQUIVO, engine='openpyxl', mode='w') as writer:
                dados.to_excel(writer, index=False)
    return redirect('/amdlanvideos')

@app.route('/amdlanrisco', methods=['GET', 'POST'])
def amdlanrisco():
    if request.method == 'POST':
        texto = request.form.get('texto')
        risco = request.form.get('risco')
        data = datetime.today().strftime('%Y-%m-%d')
        if texto and risco:
            df = pd.read_excel(arquivo_texto)
            novo = pd.DataFrame({'texto': [texto], 'risco': [risco], 'data': [data]})
            df = pd.concat([df, novo], ignore_index=True)
            df.to_excel(arquivo_texto, index=False)
        return redirect(url_for('amdlanrisco'))
    df = pd.read_excel(arquivo_texto)
    frases = df.to_dict(orient='records')
    contagens = df['risco'].value_counts().to_dict()
    return render_template('risco.html', frases=frases, contagens=contagens)

@app.route('/amdlanrisco/delete/<int:index>')
def delete_frase(index):
    df = pd.read_excel(arquivo_texto)
    if 0 <= index < len(df):
        df = df.drop(index)
        df.reset_index(drop=True, inplace=True)
        df.to_excel(arquivo_texto, index=False)
    return redirect(url_for('amdlanrisco'))

@app.route('/amdlanplanilha')
def calculo():
    return render_template('mega.html')

@app.route('/download')
def download_file():
    return send_from_directory(directory=os.path.join(os.getcwd(), 'download'), path='megazap.csv', as_attachment=True)

@app.route('/amdlanferiado', methods=['GET', 'POST'])
def amdlanferiado():
    dias_feriado = carregar_feriados()
    if request.method == 'POST':
        nova_data = request.form.get('data')
        if nova_data not in dias_feriado:
            dias_feriado.append(nova_data)
            salvar_feriado(nova_data)
        return redirect(url_for('amdlanferiado'))
    return render_template('feriado.html', feriados=dias_feriado)

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
        z = {"type": "INFORMATION",
             "text": "*Clique nos links abaixo para acessar seu boleto:\n*" + l + "Digite *#sair* para voltar pro menu principal",
             "attachments": []}
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
            keruak.append(tipo)
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
    with open("//home/flask_app//download//megazap.csv", "a") as arquivo:
        arquivo.write(f"{a};{b};{c};{d}\n")
        arquivo.close()
    return "MEGAZAP"

@app.route('/suporte', methods=['POST'])
def suporte():
    dias_feriado = carregar_feriados()
    data = request.json
    diam = datetime.now().date()
    text = data['contact']['fields']['solicitacao']
    text = text.upper()
    youtube = links(text)
    yoy = "\nSegue um video que pode te ajudar \n{}".format(youtube)
    if youtube is None:
        yoy = " "
    if datetime.today().isoweekday() == 6 or datetime.today().isoweekday() == 7 or str(diam) in dias_feriado:
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
                    data_path = '//home/flask_app//dados.xlsx'
                    model_path = '//home/flask_app//modelo.pkl'
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

@app.route('/amdlanpipe', methods=['POST'])
def amdlanpipe():
    data = request.json
    print(data)
    url = "http://191.252.178.27:3000/api/sendText"
    body = {
        "chatId": "",
        "text": "",
        "session": "default"
        }
    if data['person']['contact_phones'][0]['number'] is None:
        data['person']['contact_phones'][0]['number'] = 213555-9500
    if data['user']['name'] is None:
        data ['user']['name'] = "Maurilio"
    if data['user']['cellphone'] is None:
        data['user']['cellphone'] = "21 3555-1473"
    data['person']['contact_phones'][0]['number'] = formatar_numero(data['person']['contact_phones'][0]['number'])
    body['chatId'] = f"{data['person']['contact_phones'][0]['number']}@c.us"
    body['text'] = f"Olá, {data['person']['name']}! 👋 Tudo bem?\nAgradecemos imensamente por escolher a AMDLAN para atender às suas necessidades. É uma grande satisfação saber que nosso orçamento foi aprovado🙌😊\nQualquer coisa, é só chamar! Estamos sempre à disposição 📲😉\n\n {data['user']['name']} – AMDLAN 🚀\n 213555-9500 / {data['user']['cellphone']}"
    requests.post(url, json=body)
    return "Msg Mandada Com Sucesso"

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)



