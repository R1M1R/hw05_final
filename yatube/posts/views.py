from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page
from .forms import PostForm, CommentForm
from .models import Comment, Follow, Group, Post, User

MAGIC_NUM: int = 30
LENGTH: int = 10
User = get_user_model()


@cache_page(20)
def index(request):
    posts = Post.objects.select_related('author', 'group')
    paginator = Paginator(posts, LENGTH)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
    }
    template = "posts/index.html"
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author')
    paginator = Paginator(posts, LENGTH)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "group": group,
        "page_obj": page_obj,
        "slug": slug,
    }
    template = "posts/group_list.html"
    return render(request, template, context)


def profile(request, username):
    user = get_object_or_404(User, username=username)
    posts = user.posts.select_related('group')
    count = posts.count()
    paginator = Paginator(posts, LENGTH)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            user__exact=request.user, author__exact=user
        ).exists()
        if request.user != user.username:
            non_author = True
        else:
            non_author = False
    else:
        following = False
        non_author = False
    context = {
        "page_obj": page_obj,
        "count": count,
        "author": user,
        "following": following,
        "non_author": non_author,
    }
    template = "posts/profile.html"
    return render(request, template, context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    pub_date = post.pub_date
    post_title = post.text[:MAGIC_NUM]
    author = post.author
    author_posts = author.posts.all().count()
    comments = Comment.objects.filter(post_id__exact=post.pk)
    context = {
        "post": post,
        "post_title": post_title,
        "author": author,
        "author_posts": author_posts,
        "pub_date": pub_date,
        "form": CommentForm(),
        "comments": comments,
    }
    template = "posts/post_detail.html"
    return render(request, template, context)


@login_required
def post_create(request):
    form = PostForm(request.POST,
                    files=request.FILES or None,)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect(f"/profile/{post.author}/", {"form": form})
    form = PostForm()
    groups = Group.objects.all()
    template = "posts/create_post.html"
    context = {"form": form, "groups": groups}
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    is_edit = True
    post = get_object_or_404(Post, pk=post_id)
    author = post.author
    groups = Group.objects.all()
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    template = "posts/create_post.html"
    if author != request.user:
        return redirect("posts:post_detail", post_id)
    if form.is_valid():
        form.save()
        return redirect("posts:post_detail", post_id)
    context = {
        "form": form,
        "is_edit": is_edit,
        "post": post,
        "groups": groups,
    }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    follower_user = request.user
    following_authors = (
        Follow.objects.filter(
            author__following__user=follower_user).values("author")
    )
    posts = Post.objects.filter(author__in=following_authors)
    template = "posts/follow.html"
    paginator = Paginator(posts, settings.PER_PAGE_COUNT)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
        "following_authors": following_authors,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    following_user = request.user
    if following_user != author and following_user != author.follower:
        Follow.objects.get_or_create(user=following_user, author=author)
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    if Follow.objects.filter(user=user, author=author).exists():
        Follow.objects.filter(user=user, author=author).delete()
        return redirect("posts:profile", username=username)
    else:
        return redirect("posts:profile", username=username)
