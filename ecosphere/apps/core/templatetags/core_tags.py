from django import template
import re

register = template.Library()

@register.filter
def replace_underscore(value):
    if not value:
        return ""
    return str(value).replace("_", " ")

@register.simple_tag(takes_context=True)
def active_link(context, pattern):
    request = context.get('request')
    if not request:
        return ""
    path = request.path
    # Match root path specifically if pattern is '^/$'
    if pattern == '^/$':
        if path == '/':
            return "bg-green-500/10 text-green-400 font-medium border-l-2 border-green-500"
        return "text-gray-400 hover:bg-gray-800 hover:text-white"
    
    if re.search(pattern, path):
        return "bg-green-500/10 text-green-400 font-medium border-l-2 border-green-500"
    return "text-gray-400 hover:bg-gray-800 hover:text-white"

@register.filter
def get_enrolment(challenge, user):
    from apps.gamification.models import ChallengeEnrolment
    try:
        return ChallengeEnrolment.objects.get(challenge=challenge, employee=user)
    except Exception:
        return None

@register.filter
def is_in_list(value, lst):
    if not lst:
        return False
    return value in lst
