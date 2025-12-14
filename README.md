# 🤖 Jul.IA | Painel WhatsApp – Consignados (Frontend + Backend)

Este repositório contém:

- 🧩 **Frontend (HTML)**: painel local para copiar/colar respostas, scrapbook e aprovações.
- 🧠 **Backend (FastAPI)**: “gateway + cérebro” (rota `/ai/suggest` + webhook `/webhook`).

> **Fase atual:** roda localmente.  
> **Próxima fase:** deploy no Railway para a IA ficar online.

---

## ▶️ Rodar o Frontend
Abra no navegador:
- `frontend/Painel_WhatsApp_v4.html`

Opcional (servidor local):
```powershell
cd .\frontend
python -m http.server 5500
```

---

## 🧠 Rodar o Backend (local)
```powershell
cd .\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8020
```

Teste:
- `http://127.0.0.1:8020/health`

No painel, coloque o **apiBase** como:
- `http://127.0.0.1:8020`

---

## 🌐 Deploy no Railway (resumo)
1. Suba este repo no GitHub
2. No Railway: **New Project → Deploy from GitHub**
3. Defina variáveis (Settings → Variables):
   - `META_VERIFY_TOKEN`
   - `WHATSAPP_TOKEN`
   - (futuro) `OPENAI_API_KEY`
4. O Railway usa o `Procfile` para iniciar o servidor.

---

© 2025 Juliano Garbuggio – Advocacia & Consultoria  
Powered by Jul.IA — Inteligência Jurídica Automatizada
