from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import CreationForm


class SignUp(CreateView):
    """form_class — из какого класса взять форму
    success_url — куда перенаправить пользователя после успешной отправки формы
    template_name — имя шаблона, куда будет передана переменная form с
    объектом HTML-формы."""

    form_class = CreationForm
    success_url = reverse_lazy("posts:index")
    template_name = "users/signup.html"
