from django.contrib import admin

from dynflows.models import State, StateObjectRelation, Transition, Workflow, WorkflowObjectRelation, WorkflowModelRelation

class StateInline(admin.TabularInline):
    model = State

class WorkflowAdmin(admin.ModelAdmin):
    inlines = [
        StateInline,
    ]

admin.site.register(Workflow, WorkflowAdmin)
admin.site.register(State)
admin.site.register(StateObjectRelation)
admin.site.register(Transition)
admin.site.register(WorkflowObjectRelation)
admin.site.register(WorkflowModelRelation)

