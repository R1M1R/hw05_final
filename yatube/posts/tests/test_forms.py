import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="HasNoName")
        cls.user_two = User.objects.create_user(username="Other")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test_group",
            description="Тестовое описание группы",
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.auth_client = Client()
        self.auth_client.force_login(self.user)
        self.other_user = Client()
        self.other_user.force_login(self.user_two)

    def cheking_context(self, expect_answer):
        """Проверка контекста страниц"""
        for obj, answer in expect_answer.items():
            with self.subTest(obj=obj):
                resp_context = obj
                self.assertEqual(resp_context, answer)

    def test_create_post_without_group_authorized_user(self):
        """Валидная форма создает запись в Post. Без группы"""
        post_count = Post.objects.count()
        form_data = {
            "text": "Тестовый текст",
        }
        response = self.auth_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse("posts:profile",
                              kwargs={"username": PostFormTests.user})
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(Post.objects.order_by("-pk")[0].text,
                         form_data["text"])

    def test_create_post_with_group_authorized_user(self):
        """Валидная форма создает запись в Post. С группой"""
        post_count = Post.objects.count()
        form_data = {
            "text": "Тестовый текст 2",
            "group": PostFormTests.group.pk,
        }
        response = self.auth_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse("posts:profile",
                              kwargs={"username": PostFormTests.user})
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        last_post = Post.objects.order_by("-pk")[0]
        expect_answer = {
            last_post.group.pk: form_data["group"],
            last_post.text: form_data["text"],
        }
        self.cheking_context(expect_answer)

    def test_edit_post_without_group_authorized_user(self):
        """Валидная форма изменяет запись в Post."""
        post_new = Post.objects.create(
            author=PostFormTests.user,
            text="Текст",
        )
        form_data = {
            "text": "Тестовый текст правка",
        }
        response = self.auth_client.post(
            reverse(
                "posts:post_edit",
                kwargs={"post_id": post_new.pk},
            ),
            data=form_data,
            follow=True,
            is_edit=True,
        )
        self.assertRedirects(
            response, reverse("posts:post_detail",
                              kwargs={"post_id": post_new.pk})
        )
        self.assertTrue(
            Post.objects.filter(
                text=form_data["text"],
                id=post_new.pk,
            ).exists()
        )

    def test_edit_post_with_non_auth(self):
        """Валидная форма не изменяет запись в Post от имени не автора."""
        post_new = Post.objects.create(
            author=PostFormTests.user,
            text="Текст",
        )
        form_data = {
            "text": "Тестовый текст правка",
        }
        self.other_user.post(
            reverse(
                "posts:post_edit",
                kwargs={"post_id": post_new.pk},
            ),
            data=form_data,
            follow=True,
            is_edit=True,
        )
        post_change = Post.objects.get(
            id=post_new.pk,
        )
        expect_answer = {
            post_new.pk: post_change.pk,
            post_new.text: post_change.text,
        }
        self.cheking_context(expect_answer)

    def test_edit_post_with_group(self):
        """Валидная форма изменяет запись в Post с группой."""
        post_new = Post.objects.create(
            author=PostFormTests.user, text="Текст", group=PostFormTests.group
        )
        form_data = {
            "text": "Тестовый текст правка",
            "group": post_new.group.pk,
        }
        response = self.auth_client.post(
            reverse(
                "posts:post_edit",
                kwargs={"post_id": post_new.pk},
            ),
            data=form_data,
            follow=True,
            is_edit=True,
        )
        self.assertRedirects(
            response, reverse("posts:post_detail",
                              kwargs={"post_id": post_new.pk})
        )
        post_change = Post.objects.get(id=post_new.pk)
        expect_answer = {
            post_new.pk: post_change.pk,
            form_data["text"]: post_change.text,
            form_data["group"]: post_change.group.pk,
        }
        self.cheking_context(expect_answer)

    def test_guest_cant_create_post(self):
        """Гость не может создавать записи."""
        reverse_name = reverse('posts:post_create')
        response = self.client.post(reverse_name)
        login = reverse(settings.LOGIN_URL)
        self.assertRedirects(
            response,
            f'{login}?{REDIRECT_FIELD_NAME}={reverse_name}',
            HTTPStatus.FOUND
        )

    def test_can_edit_post(self):
        '''Проверка прав редактирования'''
        self.post = Post.objects.create(text='Тестовый текст',
                                        author=self.user,
                                        group=self.group)
        old_text = self.post
        self.group2 = Group.objects.create(title='Тестовая группа2',
                                           slug='test-group',
                                           description='Описание')
        form_data = {'text': 'Текст записанный в форму',
                     'group': self.group2.id}
        response = self.auth_client.post(
            reverse('posts:post_edit', kwargs={'post_id': old_text.id}),
            data=form_data,
            follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        error_name1 = 'Данные поста не совпадают'
        self.assertTrue(Post.objects.filter(
                        group=self.group2.id,
                        author=self.user,
                        pub_date=self.post.pub_date
                        ).exists(), error_name1)
        error_name1 = 'Пользователь не может изменить содержание поста'
        self.assertNotEqual(old_text.text, form_data['text'], error_name1)
        error_name2 = 'Пользователь не может изменить группу поста'
        self.assertNotEqual(old_text.group, form_data['group'], error_name2)

    def test_no_edit_post(self):
        '''Проверка запрета редактирования не авторизованного пользователя'''
        posts_count = Post.objects.count()
        form_data = {'text': 'Текст записанный в форму',
                     'group': self.group.id}
        response = self.guest_client.post(reverse('posts:post_create'),
                                          data=form_data,
                                          follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        error_name2 = 'Поcт добавлен в базу данных по ошибке'
        self.assertNotEqual(Post.objects.count(),
                            posts_count + 1,
                            error_name2)

    def test_create_comment_auth(self):
        """Валидная форма создает комментарий."""
        post_new = Post.objects.create(
            author=PostFormTests.user,
            text="Текст",
        )
        comments_count = Comment.objects.count()
        form_data = {
            "text": "Тестовый комментарий",
        }
        response = self.auth_client.post(
            reverse("posts:add_comment", kwargs={"post_id": post_new.pk}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse("posts:post_detail",
                              kwargs={"post_id": post_new.pk})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        last_comment = Comment.objects.order_by("-pk")[0]
        self.assertEqual(last_comment.text, form_data["text"])
        response = self.auth_client.get(
            reverse("posts:post_detail", kwargs={"post_id": post_new.pk}),
        )
        self.assertEqual(response.context["comments"][0].text,
                         form_data["text"])

    def test_create_comment_guest(self):
        """Валидная форма не создает комментарий от гостя."""
        post_new = Post.objects.create(
            author=PostFormTests.user,
            text="Текст",
        )
        comments_count = Comment.objects.count()
        form_data = {
            "text": "Тестовый комментарий",
        }
        self.client.post(
            reverse("posts:add_comment", kwargs={"post_id": post_new.pk}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), comments_count)
