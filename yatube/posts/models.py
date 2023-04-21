from django.contrib.auth import get_user_model
from django.db import models
from posts.validators import validate_not_empty

User = get_user_model()

CUT_TEXT: int = 15


class Group(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField('Текст записи', help_text='Текст вашей записи')
    pub_date = models.DateTimeField(
        'Дата публикации',
        auto_now_add=True,
        db_index=True
    )
    author = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="posts",
        verbose_name='Автор'
    )
    group = models.ForeignKey(
        Group,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='posts',
        verbose_name='Выберите сообщество:',
        help_text='Сообщество для вашей записи',
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ["-pub_date"]
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self):
        return self.text[:CUT_TEXT]


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        related_name="comments",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Cтатья с комментариями',
        help_text="",
    )
    author = models.ForeignKey(
        User, related_name="comments",
        on_delete=models.CASCADE, null=True,
        verbose_name='Автор комментария',
    )
    text = models.TextField(
        validators=[validate_not_empty],
        verbose_name='Комментарий',
        help_text='Напишите комменатрий',
    )
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации',
    )

    class Meta:
        ordering = ['-created']
        verbose_name = 'комментарий'
        verbose_name_plural = 'комментарии'

    def __str__(self):
        return self.text[:CUT_TEXT]


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        related_name="follower",
        on_delete=models.CASCADE,
        null=True,
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        User, related_name="following",
        on_delete=models.CASCADE, null=True,
        verbose_name='Отслеживается',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "author"],
                                    name="unique_following")
        ]
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
