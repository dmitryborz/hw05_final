from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.conf import settings

from .models import Post, Group, User, Comment, Follow
from .forms import PostForm, CommentForm


def paginator(posts, request):
    pag = Paginator(posts, settings.COUNT_POSTS)
    page_number = request.GET.get('page')
    return pag.get_page(page_number)


def index(request):
    post_list = Post.objects.select_related('author', 'group').all()
    page_obj = paginator(post_list, request)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author').all()
    page_obj = paginator(posts, request)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.select_related('group').all()
    page_obj = paginator(posts, request)
    template = 'posts/profile.html'
    following = (
        request.user.is_authenticated
        and Follow.objects.filter(user=request.user, author=author).exists()
    )
    context = {
        'author': author,
        'page_obj': page_obj,
        'following': following
    }
    return render(request, template, context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = Comment.objects.filter(post=post)
    context = {
        'post': post,
        'form': CommentForm(),
        'comments': comments
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=request.user.username)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = Post.objects.get(id=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post.id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        post.save()
        return redirect('posts:post_detail', post.id)
    context = {
        'form': form,
        'is_edit': True,
        'post': post}
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user.id)
    paginator = Paginator(post_list, settings.COUNT_POSTS)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    follow = True
    context = {
        'page': page,
        'paginator': paginator,
        'follow': follow
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user.username != username:
        Follow.objects.get_or_create(
            user=request.user,
            author=author
        )
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    author_username = get_object_or_404(User, username=username)
    get_object_or_404(
        Follow,
        author=author_username,
        user=request.user
    ).delete()
    return redirect('posts:profile', username=username)
