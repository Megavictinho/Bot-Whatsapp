import requests
from datetime import datetime

listaprodutos = {'cod': [], 'nome': [], 'venda': [], 'saldo': [], 'id': []}
listapipe = {'cod': [], 'pid': []}

def autenticao():
    url = "https://api.keruak.com/ws/Login/autenticar"

    headers = {
        'Authorization': '30B2E4A99C79EF119B760AD32E515E0B',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = '{"PublicKey":"92339898AC73EC119F6102E298AFB24B"}'
    resposta = requests.post(url, headers=headers, data=data)
    print("Autenticando")
    return resposta.text


def keruakprodutos():
    url = "https://api.keruak.com/ws/Produtos/lista"
    headers = {
        'Authorization': autenticao(),
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    resposta = requests.post(url, headers=headers)
    resposta = resposta.json()
    print("Buscando Produtos No Keruak")
    for zi in range(len(resposta['root'])):
        if "PRO" in resposta['root'][zi]['CodigoInterno']:
            listaprodutos['cod'].append(resposta['root'][zi]['CodigoInterno'])
            listaprodutos['nome'].append(resposta['root'][zi]['Nome'])
            listaprodutos['venda'].append((resposta['root'][zi]['ValorVenda'].replace('.', '')).replace(',', '.'))
            listaprodutos['saldo'].append(resposta['root'][zi]['Saldo'])
    print("Carregando Produtos Na Base")


def pipe():
    url = "https://api.pipe.run/v1/items?show=200&code=pro"
    headers = {
        "accept": "application/json",
        "token": "f6b26d87b309edc5fd6f8d8d6aaa1e58"
    }
    resposta = requests.get(url, headers=headers)
    resposta = resposta.json()
    print("Buscando Produtos ID No Pipe")
    for vi in range(1, (resposta['meta']['total_pages'] + 1)):
        url = "https://api.pipe.run/v1/items?show=200&page={}&code=pro".format(vi)
        headers = {
            "accept": "application/json",
            "token": "f6b26d87b309edc5fd6f8d8d6aaa1e58"
        }
        respost = requests.get(url, headers=headers)
        respost = respost.json()
        for f in range(len(respost['data'])):
            listapipe['cod'].append(respost['data'][f]['code'])
            listapipe['pid'].append(respost['data'][f]['id'])
    print("Carregando Produtos Na Base")


def atualizarpipe(py, valor, saldo):
    url = "https://api.pipe.run/v1/items/{}".format(py)
    payload = {
        "minimum_value": valor,
        "description": "Estoque: {}".format(saldo)
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "token": "f6b26d87b309edc5fd6f8d8d6aaa1e58"
    }
    response = requests.put(url, json=payload, headers=headers)


def criarpipe(nome, valor, cod, saldo):
    url = "https://api.pipe.run/v1/items"

    payload = {
        "name": nome,
        "type": 0,
        "minimum_value": valor,
        "status": True,
        "description": "Estoque: {}".format(saldo),
        "commission": 2,
        "code": cod
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "token": "f6b26d87b309edc5fd6f8d8d6aaa1e58"
    }

    response = requests.post(url, json=payload, headers=headers)

print("--------------------------------------------------")
print(datetime.now())
print("Limpando Base interna")
listaprodutos['cod'].clear()
listaprodutos['nome'].clear()
listaprodutos['venda'].clear()
listaprodutos['saldo'].clear()
listaprodutos['id'].clear()
listapipe['cod'].clear()
listapipe['pid'].clear()
print("Base interna Limpa")
keruakprodutos()
pipe()
for i in range(len(listaprodutos['cod'])):
        if listaprodutos['cod'][i] in listapipe['cod']:
            a = listapipe['cod'].index(listaprodutos['cod'][i])
            listaprodutos['id'].append(listapipe['pid'][a])
            atualizarpipe(listaprodutos['id'][i], listaprodutos['venda'][i], listaprodutos['saldo'][i])
        else:
            criarpipe(listaprodutos['nome'][i], listaprodutos['venda'][i], listaprodutos['cod'][i],listaprodutos['saldo'][i])
print(datetime.now())