from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic.base import TemplateView


class MyView(TemplateView):
  
    def get_context_data(self, **kwargs):
        context = super(MyView, self).get_context_data(**kwargs)        
        return context

def home(request,template_name="home.html"):
    return MyView.as_view(template_name=template_name)(request)
    
    