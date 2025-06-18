from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    prompt={
        "id": "pmpt_68522066d51c8197aaabf126212162c3051ff29b8249810d",  # Tu prompt guardado
        "version": "2",
        "variables": {
            "nombre": "Romina Yanet ACOSTA CENTURIÓN",
            "consigna": "3_7_tarea1",
            "resolucion": (
                "Buenas noches, comparto los desafíos de la tarea 3.7. "
                "Para resolver los desafíos utilicé el material de lectura, usando sum, min y max al calcular el promedio. "
                "El reto fue realizar la lista sin ser modificada, el método sorted permitió ordenarla sin que se generen alteraciones. "
                "Adjuntos:\n"
                "https://github.com/Romina185/Desaf-os/blob/main/Desaf%C3%ADos%203.7%20Arreglos.ipynb\n"
                "https://gitlab.com/romied29-group/romied29-project/-/tree/main"
            )
        }
    },
    tools=[
        {
            "type": "file_search",
            "vector_store_ids": [
                "vs_685220197b3c8191bb1c7e588f365d3d" # Reemplaza por tu vector store si cambia
            ]
        },
        {
            "type": "web_search_preview",
            "user_location": {
                "type": "approximate",
                "country": "UY"
            },
            "search_context_size": "medium"
        }
    ],
    max_output_tokens=2048,
    store=True
)

print(response)
