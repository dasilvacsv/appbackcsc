import sqlite3

# Conectarse a la base de datos (la crea si no existe)
conn = sqlite3.connect('usuarios.db')
c = conn.cursor()

# Crear la tabla de usuarios si no existe
# Crear la tabla de logs de transacciones si no existe
c.execute('''
DELETE FROM transacciones_canales_logs
''')


# Guardar los cambios y cerrar la conexión
conn.commit()
conn.close()