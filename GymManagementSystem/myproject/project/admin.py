from django.contrib import admin
from .models import TeamMember,Contact,add_Enquiry,add_Plan,add_Equipment,add_Member,Image

admin.site.register(TeamMember)

admin.site.register(Contact)

admin.site.register(add_Enquiry)

admin.site.register(add_Plan)

admin.site.register(add_Equipment)

admin.site.register(add_Member)

admin.site.register(Image)
