import cgi
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import webapp2


CONTENT_TEMPLATE = """\
<div>
    <b>{author}</b> wrote:
    <blockquote>{content}</blockquote>
</div>
"""

MAIN_PAGE_TEMPLATE = """\
<html>
  <body>
    <h1>Items</h1>
    {items}
    <form action="/submit?{params}" method="post">
      <div><textarea name="content" rows="3" cols="60"></textarea></div>
      <div><input type="submit" value="Create Content"></div>
    </form>
    <hr>
    <form>Category:
      <input value="{category}" name="category">
      <input type="submit" value="switch">
      <a href="/?category=default">default</a>
    </form>
    {user} <a href="{url}">{urltext}</a>
  </body>
</html>
"""


DEFAULT_CATEGORY = 'default'
category_key = lambda category=DEFAULT_CATEGORY: ndb.Key(
    'Category', category
)


class Author(ndb.Model):
    """Model for content creators."""
    identity = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)


class Content(ndb.Model):
    """Main model for content created by creators."""
    author = ndb.StructuredProperty(Author)
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)


class CategoryHandlers(object):

    def get(self):
        self.__category = None

    def post(self):
        self.__category = None
    
    @property
    def category(self):
        if self.__category is None:
            self.__category = self.request.get('category', DEFAULT_CATEGORY)
        return self.__category


class MainPage(webapp2.RequestHandler, CategoryHandlers):

    def get_content(self, category=DEFAULT_CATEGORY, n=10):
        content_query = Content.query(
            ancestor=category_key(category)
        ).order(-Content.date)
        return content_query.fetch(n)

    def get(self):
        super(MainPage, self).get()
        user = users.get_current_user()
        content_list = self.get_content(category=self.category)
        content_strings = [
            CONTENT_TEMPLATE.format(
                author=str(
                    item.author.email + \
                    ' (You)' if user and (
                        user.user_id() == item.author.identity
                    ) else item.author.email
                ) if item.author else 'An anonymous person',
                content=cgi.escape(item.content)
            )
            for item in content_list
        ]

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        # Write the submission form and the footer of the page
        self.response.write(
            MAIN_PAGE_TEMPLATE.format(
                params=urllib.urlencode({'category': self.category}), 
                category=cgi.escape(self.category),
                url=url, 
                urltext=url_linktext,
                items=''.join(content_strings),
                user=user.email(),
            )
        )


class PostContent(webapp2.RequestHandler, CategoryHandlers):

    def post(self):
        super(PostContent, self).post()
        item = Content(
            parent=category_key(self.category)
        )
        user = users.get_current_user()
        if user:
            item.author = Author(
                identity=user.user_id(),
                email=user.email()
            )

        item.content = self.request.get('content')
        item.put()

        self.redirect('/?' + urllib.urlencode({'category': self.category}))



app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/submit', PostContent),
], debug=True)