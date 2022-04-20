from http import HTTPStatus
import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
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
        context = {
            'text': 'Текстовый текст',
            'group': PostFormTest.group.id,
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
        self.assertEqual(post_last.group.id, context['group'])
        self.assertEqual(post_last.author, self.user)
        self.assertEqual(response.status_code, HTTPStatus.OK)

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
