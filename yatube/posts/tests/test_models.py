from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Comment, Follow, Group, Post

User = get_user_model()
SLICE: int = 15


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user_2 = User.objects.create_user(
            username='another_user',
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            group=PostModelTest.group,
            author=PostModelTest.user,
            text='Тестовая запись более 15 знаков',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=PostModelTest.user,
            text='Рандомный комментарий',
        )
        cls.follow = Follow.objects.create(
            user=PostModelTest.user_2,
            author=PostModelTest.user,
        )

    def test_follow_verbose_name(self):
        follow = self.follow
        field_verboses = {
            'user': 'Подписчик',
            'author': 'Отслеживается',
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                verbose_name = follow._meta.get_field(value).verbose_name
                self.assertEqual(verbose_name, expected)

    def test_object_name(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = self.post
        group = self.group
        comment = self.comment
        str_objects_names = {
            post.text[:SLICE]: str(post),
            group.title: str(group),
            comment.text[:SLICE]: str(comment),
        }
        for value, expected in str_objects_names.items():
            self.assertEqual(value, expected)
