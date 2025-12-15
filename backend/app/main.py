import os
import re
import logging
from typing import List, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Carrega variáveis do .env em ambiente local
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("julia-whatsapp-backend")

app = FastAPI(
    title="Jul.IA – Painel WhatsApp (Gateway + Cérebro)",
    version="1.0.0",
    description="Webhook WhatsApp (Meta) + API do Painel (IA sugerir)."
)

# CORS para permitir o HTML chamar a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # depois a gente trava em domínio específico
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")

# -------------------- MODELOS IA --------------------
class SuggestRequest(BaseModel):
    message: str
    profile: Optional[str] = "auto"   # ex: inss, clt, servidor
    privacy: Optional[bool] = True
    max_variations: Optional[int] = 3

class SuggestResponse(BaseModel):
    masked_message: str
    suggestions: List[str]
    tags: List[str]

# -------------------- HELPERS --------------------
def mask_sensitive(text: str) -> str:
    # CPF
    text = re.sub(r"\b(\d{3})\D?(\d{3})\D?(\d{3})\D?(\d{2})\b", r"\1.***.***-\4", text)
    # Telefones
    text = re.sub(r"\b(\+?55\s?)?(\(?\d{2}\)?\s?)?\d{4,5}-?\d{4}\b", "***telefone***", text)
    # Emails
    text = re.sub(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b", "***email***", text)
    return text

def heuristic_suggestions(msg: str, profile: str) -> SuggestResponse:
    lower = msg.lower()
    tags: List[str] = []
    suggestions: List[str] = []

    if any(k in lower for k in ["rcc", "rmc", "cartão", "cartao"]):
        tags.append("cartao-rcc-rmc")
        suggestions.append(
            "Entendi. Muitos casos de cartão consignado (RMC/RCC) são oferecidos como se fossem empréstimo comum. "
            "Se você me mandar o extrato/contracheque, eu faço uma análise gratuita e te digo se há cobrança indevida e o que dá pra pedir na ação.\n\n"
            "✅ Vantagens: parar de pagar (se ativo) + devolução do indevido (muitas vezes em dobro) + possíveis danos morais."
        )

    if any(k in lower for k in ["não tenho contrato", "nao tenho contrato", "perdi", "nunca assinei", "assinatura"]):
        tags.append("sem-contrato")
        suggestions.append(
            "Sem problema. Mesmo sem o contrato em mãos, dá pra pedir a exibição do contrato e questionar descontos/lançamentos indevidos. "
            "Em muitos casos, conseguimos parar descontos (se ativo) e buscar devolução do que foi pago indevidamente.\n\n"
            "✅ Vantagens: parar de pagar (se ativo) + restituição (às vezes em dobro) + possíveis danos morais."
        )

    if any(k in lower for k in ["quanto custa", "custas", "pagar", "honor", "juizado", "justiça gratuita", "justica gratuita"]):
        tags.append("custas-honorarios")
        suggestions.append(
            "A análise inicial é gratuita. Sobre custas: dependendo do caso, dá pra entrar com Justiça Gratuita ou pelo Juizado, onde geralmente não há custas iniciais. "
            "E se não ganharmos, você não paga nada para mim (nem sucumbência no Juizado).\n\n"
            "✅ Vantagens: parar de pagar (se ativo) + devolução do indevido (muitas vezes em dobro) + possíveis danos morais."
        )

    if not suggestions:
        tags.append("geral")
        suggestions.append(
            "Entendi. Só pra eu te orientar certinho: esses descontos aparecem no seu benefício/contracheque todo mês? "
            "Se você enviar o extrato/contracheque (principalmente os descontos), eu faço uma análise gratuita e te digo se existe irregularidade e qual o melhor caminho.\n\n"
            "✅ Vantagens: parar de pagar (se ativo) + devolução do indevido (muitas vezes em dobro) + possíveis danos morais."
        )

    # Variações (pra não ficar tudo idêntico)
    base = suggestions[0]
    variations = [base]
    if len(variations) < 3:
        variations.append(base.replace("Entendi.", "Certo.").replace("Se você enviar", "Se conseguir enviar"))
    if len(variations) < 3:
        variations.append(base.replace("Só pra eu te orientar certinho:", "Só pra eu entender melhor:"))

    return SuggestResponse(masked_message=msg, suggestions=variations[:3], tags=tags)

def extract_whatsapp_text(payload: dict) -> Optional[str]:
    """
    Extrai texto do payload padrão da Meta WhatsApp Cloud API.
    Retorna None se não houver mensagem de texto.
    """
    try:
        entry = payload.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return None
        msg = messages[0]
        if msg.get("type") == "text":
            return msg.get("text", {}).get("body")
        return None
    except Exception:
        return None

# -------------------- ROTAS --------------------
@app.get("/")
async def root():
    return {"status": "ok", "message": "Jul.IA (Gateway + Cérebro) rodando."}

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/ai/suggest", response_model=SuggestResponse)
async def ai_suggest(payload: SuggestRequest):
    msg = (payload.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message is required")
    if payload.privacy:
        msg = mask_sensitive(msg)
    return heuristic_suggestions(msg, payload.profile or "auto")

@app.get("/webhook")
async def verify(request: Request):
    """Endpoint usado pelo Meta para validar o webhook."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    logger.info("GET /webhook | mode=%s token=%s", mode, token)

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge or "")
    raise HTTPException(status_code=403, detail="Invalid verify token")

@app.post("/webhook")
async def webhook(request: Request):
    """Recebe mensagens e eventos do WhatsApp (Meta)."""
    body = await request.json()
    logger.info("POST /webhook | payload received")

    # Exemplo: extrair texto (não responde ainda)
    text = extract_whatsapp_text(body)
    if text:
        logger.info("Mensagem recebida: %s", text)

    # FUTURO: aqui a gente chama a IA real e envia resposta via Graph API
    return JSONResponse({"status": "ok"})
