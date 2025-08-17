from django.db import models


class NavMenu(models.Model):
    class MenuLocation(models.TextChoices):
        HEADER = "header", "Header"
        SIDE_LEFT = "side_left", "Side Left"
        SIDE_RIGHT = "side_right", "Side Right"
        FOOTER = "footer", "Footer"
        CONTENT = "content", "Content"

    menu_location = models.CharField(max_length=30, choices=MenuLocation.choices)
    menu_name = models.CharField(max_length=30)
    slug = models.SlugField(unique=True)
    menu_path_info = models.CharField(max_length=255)
    order = models.SmallIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.menu_name
