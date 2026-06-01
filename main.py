import os
import sqlite3
import csv
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "gastos.db")

conn = sqlite3.connect("gastos.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    valor REAL NOT NULL,
    categoria TEXT NOT NULL,
    descricao TEXT,
    data TEXT NOT NULL,
    user_id INTEGER NOT NULL
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    UNIQUE(nome, user_id)
)
""")

conn.commit()

def formatar_data(data_iso):
    return datetime.fromisoformat(data_iso).strftime("%d/%m/%Y %H:%M")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = """
<b>💰 Bot de Gastos Online!</b>

📘 <code>/ajuda</code> - Ver todos os comandos

<b>📝 Registrar</b>
➖ <code>/gasto</code>
➕ <code>/entrada</code>

<b>📊 Consultar</b>
📌 <code>/resumo</code>
📂 <code>/categorias</code>
🧾 <code>/ultimos</code>
🔎 <code>/gastos</code>
🔎 <code>/periodo</code>

<b>🏷️ Categorias</b>
➕ <code>/criar</code>
📋 <code>/minhas</code>

<b>🗑️ Gerenciar</b>
❌ <code>/apagar</code>
🧹 <code>/limpar</code>
📤 <code>/exportar</code>
"""
    await update.message.reply_text(texto, parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = """
<b>📘 Ajuda do Zezo</b>

<b>📝 Registrar transações</b>

➖ <code>/gasto 25 mercado arroz</code>
Registra um gasto.
Exemplo: gastou R$25 na categoria mercado com arroz.

➕ <code>/entrada 800 salario</code>
Registra uma entrada de dinheiro.
Exemplo: recebeu R$800 de salário.

<b>🏷️ Categorias</b>

➕ <code>/criar mercado</code>
Cria uma nova categoria.

📋 <code>/minhas</code>
Mostra todas as suas categorias criadas.

📂 <code>/categorias</code>
Mostra quanto você gastou em cada categoria.

🔎 <code>/gastos mercado</code>
Mostra todos os gastos de uma categoria específica.

<b>📊 Consultas</b>

📌 <code>/resumo</code>
Mostra entradas, gastos e saldo geral.

🧾 <code>/ultimos</code>
Mostra suas últimas transações registradas.

📅 <code>/periodo 01/06/2026 30/06/2026</code>
Mostra as transações dentro de um intervalo de datas.

<b>🗑️ Gerenciar dados</b>

❌ <code>/apagar 3</code>
Apaga uma transação pelo ID, com confirmação.

🧹 <code>/limpar</code>
Apaga todas as suas transações e categorias, com confirmação.

📤 <code>/exportar</code>
Exporta suas transações em arquivo CSV.

<b>✅ Exemplo de uso básico</b>

1. Crie uma categoria:
<code>/criar mercado</code>

2. Registre um gasto:
<code>/gasto 25 mercado arroz</code>

3. Veja o resumo:
<code>/resumo</code>

4. Veja gastos por categoria:
<code>/categorias</code>
"""
    await update.message.reply_text(texto, parse_mode="HTML")

async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(context.args[0].replace(",", "."))
        categoria = context.args[1].lower()
        descricao = " ".join(context.args[2:]) or ""
        user_id = update.effective_user.id

        cursor.execute("""
            SELECT id
            FROM categorias
            WHERE nome = ? AND user_id = ?
        """, (categoria, user_id))

        categoria_existe = cursor.fetchone()

        if not categoria_existe:
            await update.message.reply_text(
                f"A categoria '{categoria}' não existe.\n\n"
                f"Crie antes com:\n/criar {categoria}"
            )
            return

        cursor.execute("""
            INSERT INTO transacoes (tipo, valor, categoria, descricao, data, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("gasto", valor, categoria, descricao, datetime.now().isoformat(), user_id))
        conn.commit()

        await update.message.reply_text(
            f"Gasto registrado: R$ {valor:.2f} em {categoria}"
        )
    except:
        await update.message.reply_text("Use assim: /gasto 25 mercado arroz")

async def criar_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nome = " ".join(context.args).strip().lower()
        user_id = update.effective_user.id

        if not nome:
            await update.message.reply_text("Use assim: /criar CATEGORIA")
            return

        cursor.execute("""
            INSERT INTO categorias (nome, user_id)
            VALUES (?, ?)
        """, (nome, user_id))
        conn.commit()

        await update.message.reply_text(f"Categoria criada: {nome}")
    except sqlite3.IntegrityError:
        await update.message.reply_text("Essa categoria já existe.")
    except:
        await update.message.reply_text("Use assim: /criar CATEGORIA")

async def minhas_categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("""
        SELECT nome
        FROM categorias
        WHERE user_id = ?
        ORDER BY nome ASC
    """, (user_id,))

    linhas = cursor.fetchall()

    if not linhas:
        await update.message.reply_text(
            "Você ainda não criou categorias.\n\n"
            "Use: /criar CATEGORIA"
        )
        return

    texto = "Suas categorias:\n\n"
    for linha in linhas:
        texto += f"- {linha[0]}\n"

    await update.message.reply_text(texto)

async def entrada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(context.args[0].replace(",", "."))
        categoria = context.args[1]
        descricao = " ".join(context.args[2:]) or ""

        cursor.execute("""
            INSERT INTO transacoes (tipo, valor, categoria, descricao, data, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("entrada", valor, categoria, descricao, datetime.now().isoformat(), update.effective_user.id))
        conn.commit()

        await update.message.reply_text(f"Entrada registrada: R$ {valor:.2f} em {categoria}")
    except:
        await update.message.reply_text("Use assim: /entrada 800 salario")

async def resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("""
        SELECT tipo, SUM(valor)
        FROM transacoes
        WHERE user_id = ?
        GROUP BY tipo
    """, (user_id,))

    dados = dict(cursor.fetchall())
    entradas = dados.get("entrada", 0)
    gastos = dados.get("gasto", 0)

    await update.message.reply_text(
        f"Resumo geral:\n\n"
        f"Entradas: R$ {entradas:.2f}\n"
        f"Gastos: R$ {gastos:.2f}\n"
        f"Saldo: R$ {entradas - gastos:.2f}"
    )

async def gastos_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        categoria = " ".join(context.args).strip().lower()
        user_id = update.effective_user.id

        if not categoria:
            await update.message.reply_text("Use assim: /gastos mercado")
            return

        cursor.execute("""
            SELECT valor, descricao, data
            FROM transacoes
            WHERE tipo = 'gasto'
              AND categoria = ?
              AND user_id = ?
            ORDER BY data DESC
        """, (categoria, user_id))

        linhas = cursor.fetchall()

        if not linhas:
            await update.message.reply_text(
                f"Nenhum gasto encontrado na categoria '{categoria}'."
            )
            return

        total = 0
        texto = f"Gastos da categoria: {categoria}\n\n"

        for valor, descricao, data in linhas:
            total += valor
            data_formatada = formatar_data(data)
            item = descricao if descricao else "sem descrição"

            texto += f"{data_formatada}\n"
            texto += f"R$ {valor:.2f} - {item}\n\n"

        texto += f"Total: R$ {total:.2f}"

        await update.message.reply_text(texto)

    except:
        await update.message.reply_text("Use assim: /gastos CATEGORIA")

async def categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("""
        SELECT categoria, SUM(valor)
        FROM transacoes
        WHERE tipo = 'gasto' AND user_id = ?
        GROUP BY categoria
        ORDER BY SUM(valor) DESC
    """, (user_id,))

    linhas = cursor.fetchall()

    if not linhas:
        await update.message.reply_text("Nenhum gasto registrado ainda.")
        return

    texto = "Gastos por categoria:\n\n"
    for categoria, total in linhas:
        texto += f"{categoria}: R$ {total:.2f}\n"

    await update.message.reply_text(texto)

async def ultimos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("""
        SELECT id, tipo, valor, categoria, descricao, data
        FROM transacoes
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 10
    """, (user_id,))

    linhas = cursor.fetchall()

    if not linhas:
        await update.message.reply_text("Nenhuma transação registrada ainda.")
        return

    texto = "Últimas transações:\n\n"

    for id_, tipo, valor, categoria, descricao, data in linhas:
        sinal = "-" if tipo == "gasto" else "+"
        desc = f" - {descricao}" if descricao else ""
        texto += f"#{id_} | {sinal} R$ {valor:.2f} | {categoria}{desc}\n"
        texto += f"{formatar_data(data)}\n\n"

    await update.message.reply_text(texto)

async def apagar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        transacao_id = int(context.args[0])
        user_id = update.effective_user.id

        cursor.execute("""
            SELECT id, tipo, valor, categoria, descricao, data
            FROM transacoes
            WHERE id = ? AND user_id = ?
        """, (transacao_id, user_id))

        transacao = cursor.fetchone()

        if not transacao:
            await update.message.reply_text("❌ Não encontrei essa transação.")
            return

        id_, tipo, valor, categoria, descricao, data = transacao
        descricao = descricao or "sem descrição"

        texto = (
            "⚠️ <b>Confirmar exclusão</b>\n\n"
            f"<b>ID:</b> #{id_}\n"
            f"<b>Tipo:</b> {tipo}\n"
            f"<b>Valor:</b> R$ {valor:.2f}\n"
            f"<b>Categoria:</b> {categoria}\n"
            f"<b>Descrição:</b> {descricao}\n"
            f"<b>Data:</b> {formatar_data(data)}\n\n"
            "Deseja apagar esta transação?"
        )

        botoes = [
            [
                InlineKeyboardButton("🗑️ Sim, apagar", callback_data=f"confirmar_apagar:{id_}"),
                InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")
            ]
        ]

        await update.message.reply_text(
            texto,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(botoes)
        )

    except:
        await update.message.reply_text("Use assim: /apagar ID")

async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "⚠️ <b>Atenção!</b>\n\n"
        "Você está prestes a apagar:\n\n"
        "• Todas as suas transações\n"
        "• Todas as suas categorias\n\n"
        "Essa ação não poderá ser desfeita.\n\n"
        "Deseja continuar?"
    )

    botoes = [
        [
            InlineKeyboardButton("🚨 Continuar", callback_data="limpar_confirmacao_1"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")
        ]
    ]

    await update.message.reply_text(
        texto,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(botoes)
    )

async def periodo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id

        if len(context.args) != 2:
            await update.message.reply_text(
                "Use assim:\n/periodo 01/06/2026 30/06/2026"
            )
            return

        data_inicial = datetime.strptime(context.args[0], "%d/%m/%Y")
        data_final = datetime.strptime(context.args[1], "%d/%m/%Y")

        inicio = data_inicial.strftime("%Y-%m-%dT00:00:00")
        fim = data_final.strftime("%Y-%m-%dT23:59:59")

        cursor.execute("""
            SELECT id, tipo, valor, categoria, descricao, data
            FROM transacoes
            WHERE user_id = ?
              AND data BETWEEN ? AND ?
            ORDER BY data ASC
        """, (user_id, inicio, fim))

        linhas = cursor.fetchall()

        if not linhas:
            await update.message.reply_text(
                "📅 Nenhuma transação encontrada nesse período."
            )
            return

        total_entradas = 0
        total_gastos = 0

        texto = (
            f"📅 <b>Período</b>\n"
            f"{context.args[0]} até {context.args[1]}\n\n"
        )

        for id_, tipo, valor, categoria, descricao, data in linhas:
            descricao = descricao or "sem descrição"

            data_formatada = datetime.fromisoformat(data).strftime(
                "%d/%m/%Y %H:%M"
            )

            if tipo == "entrada":
                total_entradas += valor
                emoji = "➕"
            else:
                total_gastos += valor
                emoji = "➖"

            texto += (
                f"{emoji} <b>#{id_}</b> | R$ {valor:.2f}\n"
                f"📂 {categoria}\n"
                f"📝 {descricao}\n"
                f"🕒 {data_formatada}\n\n"
            )

        texto += (
            "──────────────\n"
            f"➕ Entradas: R$ {total_entradas:.2f}\n"
            f"➖ Gastos: R$ {total_gastos:.2f}\n"
            f"💳 Saldo: R$ {total_entradas - total_gastos:.2f}"
        )

        await update.message.reply_text(
            texto,
            parse_mode="HTML"
        )

    except ValueError:
        await update.message.reply_text(
            "Use datas válidas.\nExemplo:\n/periodo 01/06/2026 30/06/2026"
        )

async def botoes_confirmacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "cancelar":
        await query.edit_message_text("❌ Ação cancelada.")
        return

    if data.startswith("confirmar_apagar:"):
        transacao_id = int(data.split(":")[1])

        cursor.execute("""
            DELETE FROM transacoes
            WHERE id = ? AND user_id = ?
        """, (transacao_id, user_id))
        conn.commit()

        if cursor.rowcount == 0:
            await query.edit_message_text("❌ Essa transação não foi encontrada.")
        else:
            await query.edit_message_text(f"✅ Transação #{transacao_id} apagada.")
        return

    if data == "limpar_confirmacao_1":
        texto = (
            "🚨 <b>ÚLTIMO AVISO</b>\n\n"
            "Você realmente quer apagar TODOS os seus dados?\n\n"
            "Serão apagados:\n"
            "• Transações\n"
            "• Categorias\n\n"
            "<b>Essa ação é irreversível.</b>"
        )

        botoes = [
            [
                InlineKeyboardButton("🗑️ APAGAR TUDO", callback_data="confirmar_limpar_tudo"),
                InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")
            ]
        ]

        await query.edit_message_text(
            texto,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(botoes)
        )
        return

    if data == "confirmar_limpar_tudo":
        cursor.execute("DELETE FROM transacoes WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM categorias WHERE user_id = ?", (user_id,))
        conn.commit()

        await query.edit_message_text(
            "✅ Todos os seus dados foram apagados com sucesso."
        )
        return
        
async def exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    arquivo = f"transacoes_{user_id}.csv"

    cursor.execute("""
        SELECT id, tipo, valor, categoria, descricao, data
        FROM transacoes
        WHERE user_id = ?
        ORDER BY id ASC
    """, (user_id,))

    linhas = cursor.fetchall()

    if not linhas:
        await update.message.reply_text("Nenhuma transação para exportar.")
        return

    with open(arquivo, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "tipo", "valor", "categoria", "descricao", "data"])
        writer.writerows(linhas)

    await update.message.reply_document(document=open(arquivo, "rb"))

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("gasto", gasto))
app.add_handler(CommandHandler("entrada", entrada))
app.add_handler(CommandHandler("resumo", resumo))
app.add_handler(CommandHandler("categorias", categorias))
app.add_handler(CommandHandler("ultimos", ultimos))
app.add_handler(CommandHandler("exportar", exportar))
app.add_handler(CommandHandler("criar", criar_categoria))
app.add_handler(CommandHandler("minhas", minhas_categorias))
app.add_handler(CommandHandler("gastos", gastos_categoria))
app.add_handler(CommandHandler("apagar", apagar))
app.add_handler(CommandHandler("periodo", periodo))
app.add_handler(CommandHandler("limpar", limpar))
app.add_handler(CommandHandler("ajuda", help_command))
app.add_handler(CallbackQueryHandler(botoes_confirmacao))

app.run_polling()