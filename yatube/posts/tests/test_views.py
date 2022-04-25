import tempfile

from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from ..models import Group, Post, Follow, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.user_other = User.objects.create_user(username='Gogen')
        cls.user_another = User.objects.create_user(username='Biba')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.authorized_client_other = Client()
        cls.authorized_client_other.force_login(cls.user_other)
        cls.authorized_client_another = Client()
        cls.authorized_client_another.force_login(cls.user_another)
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded_image = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Описание тестовой группы'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded_image
        )
        cls.form_data = {
            'text': cls.post.text,
            'group': cls.group.id,
        }
        cls.new_post = cls.authorized_client.post(
            reverse('posts:post_create'),
            data=cls.form_data,
            follow=True
        )

    def check_post_context(self, post):
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.group, self.post.group)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.id, self.post.id)

    def test_pages_use_correct_template(self):
        """Во view-функциях используются правильные html-шаблоны."""
        templates_pages_names = {
            reverse('posts:index'):
                'posts/index.html',
            reverse('posts:profile',
                    kwargs={'username': self.user}):
                'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id}):
                'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}):
                'posts/create_post.html',
            reverse('posts:post_create'):
                'posts/create_post.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:follow_index'):
                'posts/follow.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_show_correct_context(self):
        """Проверка содержимого полей словаря response.context
        на совпадение с ожидаемым результатом. """
        urls = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(len(response.context['page_obj']), 2)
                post = response.context['page_obj'][1]
                self.check_post_context(post)

    def test_post_detail_page_show_correct(self):
        response = self.authorized_client.get(reverse(
            'posts:post_detail', args=[self.post.id]))
        post = response.context['post']
        self.check_post_context(post)

    def test_edit_create_form_show_correct_context(self):
        """Проверка редактирвания и создания поста."""
        urls = [
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        ]
        for path in urls:
            response = self.authorized_client.get(path)
            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.models.ModelChoiceField
            }
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_profile_show_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:profile', args=[self.user.username]))
        self.assertEqual(self.user, response.context['author'])

    def test_check_post_in_group(self):
        t_group = Group.objects.create(
            title='Заголовок',
            slug='test',
            description='Текст',
        )
        Group.objects.create(
            title='Заголовок1',
            slug='test1',
            description='Текст1',
        )
        Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=t_group,
        )
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertEqual(response.context['group'].title, self.group.title)
        self.assertEqual(response.context['group'].slug, self.group.slug)
        self.assertEqual(response.context['group'].description,
                         self.group.description)
        first_object = response.context['page_obj'][0]
        post_text = first_object.text
        post_group = first_object.group
        self.assertEqual(post_text, self.post.text)
        self.assertEqual(post_group.title, self.group.title)
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertFalse(response.context['page_obj'].has_next())

    def test_post_edit_id_edit(self):
        """Проверка переменной is_edit."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', args=[self.post.id]))
        post = response.context['is_edit']
        self.assertTrue(post)

    def test_index_page_cache(self):
        """Кэширование страницы выполняется корректно."""
        path = reverse('posts:index')
        response = self.authorized_client.get(path)
        content_before_delete = response.content
        Post.objects.last().delete()
        response = self.authorized_client.get(path)
        content_after_delete = response.content
        self.assertEqual(content_before_delete, content_after_delete)
        cache.clear()
        response = self.authorized_client.get(path)
        content_after_cache_clear = response.content
        self.assertNotEqual(content_after_cache_clear, content_before_delete)

    def test_follow(self):
        """Проверка profile_follow."""
        form_data = {
            'author': self.user,
            'user': self.user_other
        }
        response = self.authorized_client_other.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user}
            ),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile',
                kwargs={'username': self.user}
            )
        )
        self.assertTrue(
            Follow.objects.filter(
                user=self.user_other,
                author=self.user
            ).exists()
        )


class PaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовая группа',
        )
        cls.post = settings.COUNT_POSTS + settings.THREE_POSTS
        for cls.post in range(settings.COUNT_POSTS + settings.THREE_POSTS):
            cls.post = Post.objects.create(
                text='Тестовый текст',
                author=cls.user,
                group=cls.group
            )

    def test_first_page_contains_ten_records(self):
        """Главная страница отображает 10 записей."""
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']),
                         settings.COUNT_POSTS)

    def test_second_page_contains_three_records(self):
        """На второй странице должно быть три поста."""
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']),
                         settings.THREE_POSTS)

    def test_group_first_page_contains_ten_records(self):
        """Первая страница группы отображает 10 постов."""
        response = self.client.get(reverse(
            'posts:group_list', kwargs={
                'slug': PaginatorTests.group.slug
            })
        )
        self.assertEqual(len(response.context['page_obj']),
                         settings.COUNT_POSTS)

    def test_group_second_page_contains_three_records(self):
        """На вторая страницы группы должно быть три поста."""
        response = self.client.get(reverse(
            'posts:group_list', kwargs={
                'slug': PaginatorTests.group.slug
            }) + '?page=2')
        self.assertEqual(len(response.context['page_obj']),
                         settings.THREE_POSTS)

    def test_profile_first_page_contains_ten_records(self):
        """Первая страница автора отображает 10 постов."""
        response = self.client.get(reverse(
            'posts:profile', kwargs={
                'username': PaginatorTests.user.username,
            }))
        self.assertEqual(len(response.context['page_obj']),
                         settings.COUNT_POSTS)

    def test_profile_second_page_contains_three_records(self):
        """На второй странице автора должно быть три поста."""
        response = self.client.get(reverse(
            'posts:profile', kwargs={
                'username': PaginatorTests.user.username,
            }) + '?page=2')
        self.assertEqual(len(response.context['page_obj']),
                         settings.THREE_POSTS)


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
        """Проверка соответствия введенного комментария тому что появился,"""
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
