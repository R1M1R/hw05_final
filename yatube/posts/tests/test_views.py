import shutil
import tempfile
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Follow, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='Author')
        cls.user_two = User.objects.create_user(username="TestUser2")
        cls.guest_client = Client()
        cls.user_no_author = User.objects.create_user(username='NoAuthor')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.bytes_image = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.image = SimpleUploadedFile(
            name='small.gif',
            content=cls.bytes_image,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая запись',
            group=cls.group,
            image=cls.image
        )
        cls.comment_1 = Comment.objects.create(
            author=cls.user,
            text='Комментарий к посту 1',
            post_id=cls.post.id
        )
        cls.post_detail_url = (
            'posts:post_detail', 'posts/post_detail.html', (cls.post.id,)
        )
        cls.post_qty = Post.objects.count()
        cls.urls = (
            ('posts:index', None, 'posts/index.html'),
            ('posts:profile', (cls.user,), 'posts/profile.html'),
            ('posts:group_list', (cls.group.slug,), 'posts/group_list.html'),
            ('posts:post_detail', (cls.post.id,), 'posts/post_detail.html'),
            ('posts:post_create', None, 'posts/create_post.html'),
            ('posts:post_edit', (cls.post.id,), 'posts/create_post.html'),
            ('posts:profile_follow', (cls.user,), None),
            ('posts:profile_unfollow', (cls.user,), None),
            ('posts:add_comment', (cls.post.id,), None),
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_no_author = Client()
        self.authorized_client_no_author.force_login(self.user_no_author)
        cache.clear()

    def test_views_correct_template(self):
        '''URL-адрес использует соответствующий шаблон.'''
        templates_url_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug':
                            f'{self.group.slug}'}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username':
                            f'{self.user.username}'}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id':
                            self.post.id}): 'posts/post_detail.html',
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                error_name = f'Ошибка: {adress} ожидал шаблон {template}'
                self.assertTemplateUsed(response, template, error_name)

    def test_pages_uses_correct_template_auth_user(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}
                    ): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.user}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={
                        'post_id': self.post.pk}): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    kwargs={
                        'post_id': self.post.pk}): 'posts/create_post.html',
        }
        for url, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def check_context(self, response, bool=False):
        """Функция для передачи контекста."""
        if bool:
            post = response.context.get('post')
        else:
            post = response.context['page_obj'][0]
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.pub_date, self.post.pub_date)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.image, f'posts/{self.image}')

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_context(response)
        self.assertContains(response, '<img', count=2)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=(self.user,))
        )
        self.check_context(response)
        self.assertEqual(response.context.get('author'), self.user)
        self.assertContains(response, '<img', count=2)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', args=(self.group.slug,))
        )
        self.check_context(response)
        self.assertEqual(response.context.get('group'), self.group)
        self.assertContains(response, '<img', count=1)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""

        response = self.authorized_client.get(
            reverse('posts:post_detail', args=(self.post.id,))
        )
        self.check_context(response, True)
        self.assertContains(response, '<img', count=2)

    def test_create_edit_page_show_correct_form(self):
        """post_create и post_edit сформированы с правильным контекстом."""
        urls = (
            ('posts:post_create', None),
            ('posts:post_edit', (self.post.id,)),
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ChoiceField,
        }
        for url, slug in urls:
            reverse_name = reverse(url, args=slug)
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context.get('form').fields.get(
                            value
                        )
                        self.assertIsInstance(form_field, expected)
                        self.assertIsInstance(response.context['form'],
                                              PostForm)

    def test_post_added_correctly_user2(self):
        """Пост при создании не добавляется другому пользователю
           Но виден на главной и в группе"""
        group2 = Group.objects.create(title='Тестовая группа 2',
                                      slug='test_group2')
        posts_count = Post.objects.filter(group=self.group).count()
        post = Post.objects.create(
            text='Тестовый пост от другого автора',
            author=self.user_no_author,
            group=group2)
        response_profile = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': f'{self.user.username}'}))
        group = Post.objects.filter(group=self.group).count()
        profile = response_profile.context['page_obj']
        self.assertEqual(group, posts_count, 'поста нет в другой группе')
        self.assertNotIn(post, profile,
                         'поста нет в группе другого пользователя')

    def test_post_added_correctly(self):
        """Пост при создании добавлен корректно"""
        post = Post.objects.create(
            text='Тестовый текст проверка как добавился',
            author=self.user,
            group=self.group)
        response_index = self.authorized_client.get(
            reverse('posts:index'))
        response_group = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': f'{self.group.slug}'}))
        response_profile = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': f'{self.user.username}'}))
        index = response_index.context['page_obj']
        group = response_group.context['page_obj']
        profile = response_profile.context['page_obj']
        self.assertIn(post, index, 'поста нет на главной')
        self.assertIn(post, group, 'поста нет в профиле')
        self.assertIn(post, profile, 'поста нет в группе')

    def test_check_group_not_in_mistake_group_list_page(self):
        """Проверяем чтобы созданный Пост с группой не попап в чужую группу."""
        form_fields = {
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ): Post.objects.exclude(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context["page_obj"]
                self.assertNotIn(expected, form_field)

    def test_cache(self):
        """Проверка работы кэша."""
        post = Post.objects.create(
            author=self.user,
            text='Пост для проверки кэша',
            group=self.group
        )
        response_1 = self.client.get(reverse('posts:index'))
        self.assertTrue(Post.objects.get(pk=post.id))
        Post.objects.get(pk=post.id).delete()
        cache.clear()
        response_3 = self.client.get(reverse('posts:index'))
        self.assertNotEqual(response_1.content, response_3.content)

    def test_users_can_follow_and_unfollow(self):
        """Зарегистрированный пользователь может подписаться и отписаться."""
        follower_qty = Follow.objects.count()
        response = self.authorized_client_no_author.get(
            reverse('posts:profile_follow', args=(self.user,))
        )
        self.assertRedirects(
            response, reverse('posts:profile', args=(self.user,)),
            HTTPStatus.FOUND
        )
        self.assertEqual(Follow.objects.count(), follower_qty + 1)
        response = self.authorized_client_no_author.get(
            reverse('posts:profile_unfollow', args=(self.user,))
        )
        self.assertRedirects(
            response, reverse('posts:profile', args=(self.user,)),
            HTTPStatus.FOUND
        )
        self.assertEqual(Follow.objects.count(), follower_qty)

    def test_follow_index_page_(self):
        """Новая запись пользователя появляется в ленте followers
        и не появляется в ленте остальных.
        """
        new_user = User.objects.create_user(username="TestFollow")
        new_client = Client()
        new_client.force_login(new_user)
        new_client.post(
            reverse(
                "posts:profile_follow",
                kwargs={"username": str(PostViewsTests.user_two)},
            )
        )
        new_post = Post.objects.create(
            author=PostViewsTests.user_two,
            text="Текст для теста follow.",
        )
        response = self.authorized_client.get(reverse("posts:follow_index"))
        response_new_user = new_client.get(reverse("posts:follow_index"))
        self.assertIn(new_post,
                      response_new_user.context["page_obj"].object_list)
        self.assertNotIn(new_post, response.context["page_obj"].object_list)

    def test_double_follow(self):
        """"Проверка проверка на повторную подписку"""
        Follow.objects.create(
            user=self.user,
            author=self.user_two,
        )
        with self.assertRaises(IntegrityError):
            Follow.objects.create(user=self.user, author=self.user_two)
    
    def test_no_self_follow(self):
        """"Проверка подписки на себя"""
        constraint_name = "prevent_self_follow"
        with self.assertRaisesMessage(IntegrityError, constraint_name):
            Follow.objects.create(user=self.user, author=self.user)

    def test_commentary_for_add_comment(self):
        """"Проверка отправки комментария на страницу поста"""
        comment_post = Comment.objects.create(
            post=self.post,
            author=self.user,
            text='test_comment_text'
        )
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}))
        context_objects = response.context['comments'][0]
        self.assertEqual(context_objects.text, comment_post.text)

    def test_add_comment(self):
        """"Проверка добавления коменнтария пользователем"""
        comment_count = Comment.objects.count()
        form_data = {
            'post': self.post,
            'author': self.user,
            'text': 'test_comment_text'
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk}))
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text='test_comment_text',
            ).exists()
        )

    def test_comments_only_for_authorized_guests(self):
        """Создавать комментарий неавторизованный пользователь не может"""
        form_data = {"text": "text"}
        response = self.guest_client.post(
            reverse("posts:add_comment", kwargs={"post_id": self.post.pk}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, f"/auth/login/?next=/posts/{self.post.pk}/comment/"
        )
