import gradio as gr
from main import app

# Создаем интерфейс Gradio поверх Flask приложения
def create_gr_interface():
    return gr.Interface.from_webapp(app)

# Запускаем интерфейс
if __name__ == "__main__":
    interface = create_gr_interface()
    interface.launch()
