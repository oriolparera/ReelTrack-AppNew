import openai
import config
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain.chains import create_sql_query_chain
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from openai import OpenAI
from langdetect import detect

# Configurar la API Key
client = OpenAI(api_key=config.OPENAI_API_KEY)

# Configurar la base de datos
db_path = "bobines.db"
engine = create_engine(f"sqlite:///{db_path}")
db = SQLDatabase(engine)

# Modelo LLM para consultas SQL
llm = ChatOpenAI(
    temperature=0.5,
    model_name='gpt-3.5-turbo',
    openai_api_key=config.OPENAI_API_KEY
)

# Crear cadena de consulta SQL con LangChain
cadena = create_sql_query_chain(llm, db)

def necesita_sql(input_usuario):
    palabras_clave = ["cuántas", "cuánto", "dame", "muestra", "listado", "registros", "id", "producto", "how", "show", "list", "product", "records"]
    return any(palabra in input_usuario.lower() for palabra in palabras_clave)

def detectar_idioma(texto):
    try:
        return detect(texto)
    except Exception:
        return 'en'  # Predeterminado a inglés si la detección falla

def agregar_unidades(columna, valor):
    unidades = {
        "tension": "N",  # Newtons
        "gruix": "µm",  # Milímetros
        "amplada": "mm",  # Metros
        "longitud": "m"  # Metros
    }
    try:
        valor_numerico = float(valor)
        return f"{valor_numerico:.2f} {unidades[columna]}" if columna in unidades else str(valor)
    except (ValueError, TypeError):
        return str(valor)

def consulta(input_usuario):
    try:
        idioma = detectar_idioma(input_usuario)

        if not necesita_sql(input_usuario):
            system_message = "Provide clear and precise responses in a professional and respectful tone."
            if idioma == 'es':
                system_message = "Proporcione respuestas claras y precisas con un tono profesional y respetuoso."

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": input_usuario}
                ]
            )
            return response.choices[0].message.content

        query_result = cadena.invoke({"question": input_usuario})
        if not isinstance(query_result, str) or not query_result.strip():
            return "No se pudo generar una consulta válida. Por favor, reformule su pregunta." if idioma == 'es' else "A valid query could not be generated. Please rephrase your question."

        query = query_result.strip()
        print(f"🔍 Consulta SQL generada: {query}")

        query_lower = query.lower()
        if any(kw in query_lower for kw in ["drop", "delete", "update", "insert"]):
            return "Por razones de seguridad, no está permitido modificar la base de datos." if idioma == 'es' else "For security reasons, modifying the database is not allowed."

        with engine.connect() as connection:
            result = connection.execute(text(query))
            data = result.fetchall()
            column_names = result.keys()

        if not data:
            return "No se encontró información relevante en la base de datos." if idioma == 'es' else "No relevant information was found in the database."

        # Formatear la respuesta con unidades si corresponde
        formatted_rows = []
        for row in data:
            formatted_row = [agregar_unidades(col, val) for col, val in zip(column_names, row)]
            formatted_rows.append(" | ".join(formatted_row))

        formatted_response = "\n".join(formatted_rows)
        return f"📊 *Aquí están los resultados de su consulta:*\n\n{formatted_response}" if idioma == 'es' else f"📊 *Here are the results of your query:*\n\n{formatted_response}"

    except openai.OpenAIError as api_error:
        return f"Error en la API de OpenAI: {str(api_error)}."
    except SQLAlchemyError as db_error:
        return f"Error en la base de datos: {str(db_error)}."
    except Exception as e:
        return f"Ha ocurrido un error inesperado: {str(e)}."
