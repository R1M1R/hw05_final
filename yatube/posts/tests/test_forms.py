import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
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
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая запись',
            group=cls.group,
        )
        cls.post_qty = Post.objects.count()

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

    def test_create_form(self):
        """Валидная форма create создает запись в Post."""
        bytes_image = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        image = SimpleUploadedFile(
            name='new_small.gif',
            content=bytes_image,
            content_type='image/gif'
        )
        form_data = {
            'text': self.post.text,
            'group': self.group.pk,
            'image': image,
        }
        response = self.auth_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, reverse(
            'posts:profile', args=(self.user,)),
            HTTPStatus.FOUND
        )
        self.assertEqual(Post.objects.count(), self.post_qty + 1)
        post = Post.objects.get(pk=2)
        check_post_fields = (
            (post.author, self.post.author),
            (post.text, self.post.text),
            (post.group, self.group),
            (post.image, f'posts/{image}'),
        )
        for new_post, expected in check_post_fields:
            with self.subTest(new_post=expected):
                self.assertEqual(new_post, expected)

        response = self.auth_client.get(reverse(
            'posts:group_list', args=(self.group.slug,))
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(
            response.context['page_obj']), Post.objects.count()
        )

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

    def test_comment_cant_comment(self):
        """Комментарии не могут оставлять гости."""
        comment_data = {
            'text': 'тестовый коммент',
        }
        comments_count = Comment.objects.count()
        reverse_name = reverse('posts:add_comment', args=(self.post.id,))
        response = self.client.post(
            reverse_name,
            data=comment_data,
            follow=True,
        )
        login = reverse(settings.LOGIN_URL)
        self.assertRedirects(
            response,
            f'{login}?{REDIRECT_FIELD_NAME}={reverse_name}',
            HTTPStatus.FOUND
        )
        self.assertEqual(Comment.objects.count(), comments_count)
