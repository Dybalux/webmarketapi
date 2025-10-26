import venv
import os
import sys

# El nombre de la carpeta para el entorno virtual
NOMBRE_CARPETA = "venv"

print(f"Iniciando la creación del entorno virtual '{NOMBRE_CARPETA}'...")

# Comprobamos si la carpeta ya existe
if os.path.exists(NOMBRE_CARPETA):
    print(f"¡Error! La carpeta '{NOMBRE_CARPETA}' ya existe.")
    print("Si quieres recrearlo, borra la carpeta 'venv' e intenta de nuevo.")
    sys.exit(1) # Salimos del script con un código de error

try:
    # Creamos el entorno virtual
    # 'with_pip=True' asegura que pip esté instalado en el nuevo entorno
    venv.create(NOMBRE_CARPETA, with_pip=True)
    
    print("\n¡Éxito! Entorno virtual creado en la carpeta 'venv'.")
    print("---")
    print("Recuerda activarlo para poder usarlo.")

except Exception as e:
    print(f"Ocurrió un error inesperado durante la creación: {e}")


