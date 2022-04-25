from http import HTTPStatus
import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import Group, Post, Comment
from ..forms import CommentForm

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тест группа',
            slug='testgroup',
            description='Тест описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )
        cls.form_data = {
            'text': cls.post.text,
            'group': cls.group.id,
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTest.user)
        self.guest_client = Client()

    def test_create_post(self):
        """при отправке валидной формы со страницы создания поста
        reverse('posts:post_create') создаётся новая запись в базе данных."""
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded_image = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        context = {
            'text': 'Текстовый текст',
            'group': PostFormTest.group.id,
            'image': uploaded_image,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=context,
            follow=True
        )
        post_last = Post.objects.latest('id')
        self.assertRedirects(response,
                             reverse('posts:profile',
                                     kwargs={'username': PostFormTest.user}
                                     )
                             )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(post_last.text, context['text'])
        self.assertEqual(post_last.group.id, context['group'])
        self.assertEqual(post_last.author, self.user)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(post_last.image, f'posts/{uploaded_image.name}')

    def test_edit_post(self):
        """При отправке валидной формы со страницы редактирования поста
        reverse('posts:post_edit', args=('post_id',))
        происходит изменение поста с post_id в базе данных."""
        post_count = Post.objects.count()
        context = {
            'text': 'Тестовый текст',
            'group': ''
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={
                'post_id': PostFormTest.post.id}),
            data=context,
            follow=True
        )
        post_bd = Post.objects.get(id=PostFormTest.post.id)
        self.assertEqual(PostFormTest.post.author, post_bd.author)
        self.assertEqual(post_bd.group, None)
        self.assertEqual(PostFormTest.post.pub_date, post_bd.pub_date)
        self.assertEqual(post_bd.text, context['text'])
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': PostFormTest.post.id}))
        self.assertEqual(Post.objects.count(), post_count)

    def test_anonim_client_create_post(self):
        """При создании поста гостевого пользователя
        перебрасывает на страницу логин и затем создать пост."""
        post_count = Post.objects.count()
        response = self.client.post(
            reverse('posts:post_create'),
            data=PostFormTest.form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count)
        self.assertRedirects(response,
                             reverse('users:login') + '?next=' + reverse(
                                 'posts:post_create'))

    def test_anonim_edit_post(self):
        """Изменение поста анонимным пользователем.
        Перебрасывает на логин и потом на редактирование поста."""
        context = {
            'text': 'Попытка изменить пост',
            'group': ''
        }
        response = self.client.post(
            reverse('posts:post_edit', kwargs={
                'post_id': PostFormTest.post.id}),
            data=context,
            follow=True
        )
        kwargs = {'post_id': PostFormTest.post.id}
        self.assertRedirects(response,
                             f"{reverse('users:login')}"
                             f"?next="
                             f"{reverse('posts:post_edit', kwargs = kwargs)}"
                             )
        self.assertNotEqual(PostFormTest.post.text, context['text'])
        self.assertNotEqual(PostFormTest.post.group, None)

    def test_create_post_no_group(self):
        """Создание поста авторизованным,
        без указания группы."""
        post_count = Post.objects.count()
        context = {
            'text': 'Текстовый текст',
            'group': '',
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=context,
            follow=True
        )
        post_last = Post.objects.latest('id')
        self.assertRedirects(response,
                             reverse('posts:profile',
                                     kwargs={
                                         'username': PostFormTest.user}))
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(post_last.text, context['text'])
        self.assertEqual(post_last.author, self.user)
        self.assertEqual(response.status_code, HTTPStatus.OK)


class CommentFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый текст',
            post=cls.post
        )

    def setUp(self):
        self.guest_client = Client()
        self.author_client = Client()
        self.author_client.force_login(self.user)

    def test_add_comment(self):
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.author_client.post(
            reverse('posts:add_comment', args=[self.post.id]),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse('posts:post_detail', args=[self.post.id]))
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text=form_data['text'],
            ).exists()
        )

    def test_add_comment_guest(self):
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', args=[self.post.id]),
            data=form_data
        )
        self.assertRedirects(response,
                             f"{reverse('users:login')}"
                             f"?next="
                             f"{reverse('posts:add_comment', args=[self.post.id])}"
                             )
        self.assertEqual(Comment.objects.count(), comment_count)


