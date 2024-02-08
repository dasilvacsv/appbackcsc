import sqlite3
import matplotlib.pyplot as plt
import pandas as pd

# Conectarse a la base de datos (la crea si no existe)
def generate_transaction_table(db_path, channel_id):
    conn = sqlite3.connect('usuarios.db')
    c = conn.cursor()
    query = '''
        SELECT timestamp, operacion, cantidad, valor_anterior, nuevo_valor 
        FROM transacciones_canales_logs 
        WHERE channel_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 10
    '''
    # Ejecutar la consulta y obtener los datos
    df = pd.read_sql_query(query, conn, params=(channel_id,))

    # Verificar si hay datos
    if df.empty:
        print("No hay transacciones para mostrar.")
        return
    
    # Crear una figura y una tabla usando Matplotlib
    fig, ax = plt.subplots(figsize=(12, 2))  # Tamaño de la figura ajustable
    ax.axis('off')  # No mostrar ejes
    table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)  # Escalar la tabla

    # Guardar la figura en un archivo
    plt.savefig('historial.png')
    plt.close(fig)  # Cerrar la figura para liberar memoria
    conn.close()  # Cerrar la conexión a la base de datos

# Llamar a la función con el path a la base de datos y el ID del canal
generate_transaction_table('usuarios.db', 'tu_channel_id')
# Guardar los cambios y cerrar la conexión
