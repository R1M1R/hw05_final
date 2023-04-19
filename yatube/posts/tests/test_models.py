from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()
SLICE: int = 15


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая запись более 15 знаков',
        )

    def test_models_have_correct_title_names(self):
        """Проверяем, что у моделей Group и Post корректно работает __str__."""
        title = (
            (self.group, self.group.title),
            (self.post, self.post.text[:SLICE]),
        )
        for text, expected_name in title:
            with self.subTest(expected_name=text):
                self.assertEqual(expected_name, str(text))
