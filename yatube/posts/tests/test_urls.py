from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, Comment

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_author')
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост бла бла бла',
            group=cls.group,
        )

    def setUp(self):
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)
        self.client = Client()

    def test_urls_available(self):
        """Проверка доступности страниц."""
        all_users_urls = [
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.author.username}/',
            f'/posts/{self.post.pk}/',
        ]
        for address in all_users_urls:
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.authorized_user.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.authorized_author.get(f'/posts/{self.post.pk}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_404(self):
        """Запрос к несуществующей странице вернёт ошибку 404."""
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_redirect(self):
        """Если пользователь не авторизован, при попытке создать
        или изменить пост, его редиректнет на страницу регистрации.
        Если пользователь зарегистрирован но не является автором поста,
        его редиректнет на страницу поста."""
        urls_names = [
            '/create/',
            f'/posts/{self.post.pk}/edit/',
        ]
        for address in urls_names:
            with self.subTest(address=address):
                response = self.client.get(address, follow=True)
                self.assertRedirects(
                    response, (
                        f'/auth/login/?next={address}'
                    )
                )
        response = self.authorized_user.get(
            f'/posts/{self.post.pk}/edit/', follow=True
        )
        self.assertRedirects(
            response, (
                f'/posts/{self.post.pk}/'
            )
        )

    def test_templates(self):
        """Проыерка соответствия названий шаблонам приложения."""
        url_templates_names = {
            '/': 'posts/index.html',
            '/create/': 'posts/create_post.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.author.username}/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'posts/post_detail.html',
            f'/posts/{self.post.pk}/edit/': 'posts/create_post.html',
        }
        for reverse_name, template in url_templates_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertTemplateUsed(response, template)


class CommentTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.commentator = User.objects.create_user(username='commentator')
        cls.commentator_client = Client()
        cls.commentator_client.force_login(cls.commentator)
        cls.post = Post.objects.create(
            text='Тестовый текст поста',
            author=cls.author
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.commentator,
            text='Тестовый текст комментария'
        )

    def test_comment(self):
        """Проверка появления комментария к посту."""
        self.assertTrue(
            Comment.objects.filter(
                post=self.post,
                author=self.commentator,
                text='Тестовый текст комментария'
            ).exists
        )
        response = Comment.objects.filter(
            post=self.post,
            author=self.commentator,
            text='Тестовый текст комментария'
        ).count()
        self.assertEqual(response, 1)

    def test_comment_context(self):
        """Комментировать посты может только авторизованный пользователь."""
        response = self.commentator_client.get(
            reverse('posts:post_detail', args=[self.post.id]))
        comments = response.context['comments'][0]
        expected_fields = {
            comments.author.username: 'commentator',
            comments.post.id: self.post.id,
            comments.text: 'Тестовый текст комментария'
        }
        for fields, values in expected_fields.items():
            with self.subTest(expected_fields=expected_fields):
                self.assertEqual(fields, values)
