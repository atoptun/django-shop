from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(
                choices=[
                    ("5", "5 ★★★★★"),
                    ("4", "4 ★★★★☆"),
                    ("3", "3 ★★★☆☆"),
                    ("2", "2 ★★☆☆☆"),
                    ("1", "1 ★☆☆☆☆"),
                ],
                attrs={"class": "Select"},
            ),
            "comment": forms.Textarea(
                attrs={
                    "class": "Textarea",
                    "rows": 4,
                    "placeholder": "Write your review here...",
                }
            ),
        }
