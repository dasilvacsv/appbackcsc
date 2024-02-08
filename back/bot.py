import discord
from discord.ext import commands
import aiosqlite
import matplotlib.pyplot as plt
import pandas as pd
import io


# Define los intents que tu bot necesitará.
intents = discord.Intents.default()
intents = discord.Intents().all()

# Instancia el bot con los intents.
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command()
async def a(ctx, operacion: str, cantidad: int):
    user_id = str(ctx.author.id)

    async with aiosqlite.connect('usuarios.db') as db:
        cursor = await db.execute('SELECT valor FROM usuarios WHERE id = ?', (user_id,))
        row = await cursor.fetchone()
        valor_anterior = 0 if row is None else row[0]

        if row:
            # Usuario existe, actualizar su valor
            if operacion == 's':
                nuevo_valor = valor_anterior + cantidad
            elif operacion == 'r':
                nuevo_valor = valor_anterior - cantidad
            else:
                await ctx.send('La operación debe ser "sumar" o "restar".')
                return
            await db.execute('UPDATE usuarios SET valor = ? WHERE id = ?', (nuevo_valor, user_id))
        else:
            # Usuario nuevo, insertarlo en la base de datos
            nuevo_valor = cantidad if operacion == 's' else -cantidad
            await db.execute('INSERT INTO usuarios (id, valor) VALUES (?, ?)', (user_id, nuevo_valor))

         # Insertar el log de la transacción
        await db.execute('''
            INSERT INTO transacciones_logs (user_id, operacion, cantidad, valor_anterior, nuevo_valor) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, operacion, cantidad, valor_anterior, nuevo_valor))

        await db.commit()

    await ctx.send(f'Valor actualizado de {valor_anterior} a {nuevo_valor} ({operacion} {cantidad})')

@a.error
async def actualizar_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Falta un argumento requerido. Uso correcto: `!actualizar <operacion> <cantidad>`')
    else:
        raise error
    

@bot.command()
async def b(ctx, operacion: str, cantidad_primaria: int, cantidad_secundaria: int = 0):
    channel_id = str(ctx.channel.id)

    async with aiosqlite.connect('usuarios.db') as db:
        cursor = await db.execute('SELECT valor, secondary_value FROM canales WHERE id = ?', (channel_id,))
        row = await cursor.fetchone()
        valor_anterior, secondary_anterior = (0, 0) if row is None else row

        # Determinar la operación para el valor primario
        nuevo_valor = valor_anterior + abs(cantidad_primaria) if operacion == '+' else valor_anterior - abs(cantidad_primaria)
        
        # La segunda operación es inversa a la primera
        secondary_nuevo = secondary_anterior - abs(cantidad_secundaria) if operacion == '+' else secondary_anterior + abs(cantidad_secundaria)

        # Realizar la actualización o la inserción según corresponda
        if row:
            await db.execute('UPDATE canales SET valor = ?, secondary_value = ? WHERE id = ?', (nuevo_valor, secondary_nuevo, channel_id))
        else:
            await db.execute('INSERT INTO canales (id, valor, secondary_value) VALUES (?, ?, ?)', (channel_id, nuevo_valor, secondary_nuevo))

        # Insertar el log de la transacción para el canal
        await db.execute('''
            INSERT INTO transacciones_canales_logs (channel_id, operacion, cantidad_primaria, cantidad_secundaria, valor_anterior, nuevo_valor, secondary_anterior, secondary_nuevo) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (channel_id, operacion, cantidad_primaria, cantidad_secundaria, valor_anterior, nuevo_valor, secondary_anterior, secondary_nuevo))

        await db.commit()

    # Formatear el mensaje para enviar
    signo_primario = "+" if operacion == '+' else "-"
    signo_secundario = "-" if operacion == '+' else "+"
    await ctx.send(f'Valor primario del canal actualizado de {valor_anterior} a {nuevo_valor} ({signo_primario}{abs(cantidad_primaria)}), '
                   f'Valor secundario del canal actualizado de {secondary_anterior} a {secondary_nuevo} ({signo_secundario}{abs(cantidad_secundaria)})')

@bot.command()
async def historial(ctx):
    # Connect to the database and retrieve transaction records
    async with aiosqlite.connect('usuarios.db') as db:
        cursor = await db.execute('''
            SELECT timestamp, operacion, cantidad_primaria, cantidad_secundaria, valor_anterior, nuevo_valor, secondary_anterior, secondary_nuevo
            FROM transacciones_canales_logs
            WHERE channel_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (str(ctx.channel.id),))
        rows = await cursor.fetchall()

    # Table headers
    headers = ["Fecha", "Operación", "Cantidad Primaria", "Cantidad Secundaria", "Valor Anterior", "Valor Nuevo", "Secundario Anterior", "Secundario Nuevo"]

    # Table data
    data = []
    for row in rows:
        # Parse the date into a readable format
        fecha = row[0]  # Assuming timestamp is the first column
        operacion = row[1]
        cantidad_primaria = f"{row[2]:,.2f} Bs."
        cantidad_secundaria = f"{row[3]:,.2f} Bs."
        valor_anterior = f"{row[4]:,.2f} Bs."
        nuevo_valor = f"{row[5]:,.2f} Bs."
        secondary_anterior = f"{row[6]:,.2f} Bs."
        secondary_nuevo = f"{row[7]:,.2f} Bs."
        
        # Add the row to the data
        data.append([fecha, operacion, cantidad_primaria, cantidad_secundaria, valor_anterior, nuevo_valor, secondary_anterior, secondary_nuevo])

    # Convert the data to an ASCII table
    tabla = "```"  # Use triple backticks for code block formatting in Discord
    tabla += "\n".join(["\t".join(headers)] + ["\t".join(map(str, row)) for row in data])
    tabla += "```"

    # Send the message to the Discord channel
    await ctx.send(tabla)

@bot.command()
async def reiniciar_canal(ctx):
    channel_id = str(ctx.channel.id)

    async with aiosqlite.connect('usuarios.db') as db:
        # Check if the channel already has a registered value
        cursor = await db.execute('SELECT valor, secondary_value FROM canales WHERE id = ?', (channel_id,))
        row = await cursor.fetchone()

        if row:
            # Reset the existing channel's valor and secondary_value to 0
            await db.execute('UPDATE canales SET valor = 0, secondary_value = 0 WHERE id = ?', (channel_id,))
            valor_anterior, secondary_anterior = row
        else:
            # If not, insert a new channel with valor and secondary_value as 0
            await db.execute('INSERT INTO canales (id, valor, secondary_value) VALUES (?, 0, 0)', (channel_id,))
            valor_anterior, secondary_anterior = (0, 0)

        # Insert the reset transaction log for the channel
        await db.execute('''
            INSERT INTO transacciones_canales_logs (channel_id, operacion, cantidad_primaria, cantidad_secundaria, valor_anterior, nuevo_valor, secondary_anterior, secondary_nuevo) 
            VALUES (?, 'reinicio', 0, 0, ?, 0, ?, 0)
        ''', (channel_id, valor_anterior, secondary_anterior))

        await db.commit()

    await ctx.send(f'Los valores del canal {ctx.channel.name} han sido reiniciados a 0.')

###########

# Inicia el bot
bot.run('MTIwNDgwMDIyODEyNjEwMTU2NQ.GSVMMQ.KNzz_OEtrK5UVq-ZoJQm7sJR9dYqV9lglBnzOU')

