from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

class Workflow(models.Model):
    """
    A workflow consists of a sequence of connected (through transitions)
    states. It can be assigned to a model and / or model instances. If a
    model instance has a workflow it takes precendence over the model's
    workflow.

    **Attributes:**

    model
        The model the workflow belongs to. Can be any

    content
        The object the workflow belongs to.

    name
        The unique name of the workflow.

    states
        The states of the workflow.

    initial_state
        The initial state the model / content gets if created.
    """
    
    name = models.CharField(_(u"Name"), max_length=100, unique=True)
    initial_state = models.ForeignKey("State", verbose_name=_(u"Initial state"), related_name="workflow_state", blank=True, null=True)
    # FIXME: ``symmetrical`` should make sense only for relationship within the same model

    def __unicode__(self):
        return self.name
    
    # FIXME: should be a property
    def get_initial_state(self):
        """
        
        Returns the initial state of the workflow. Takes the first one if
        no state has been defined.
        """
        if self.initial_state:
            return self.initial_state
        else:
            try:
                return self.states.all()[0]
            except IndexError:
                # FIXME: should raise an exception, instead !
                return None

    def get_objects(self):
        """
        Returns all objects which have this workflow assigned. Globally
        (via the object's content type) or locally (via the object itself).        
        """
        
        from dynflows import utils
        
        objs = []

        # Get all objects whose content type has this workflow
        for wmr in WorkflowModelRelation.objects.filter(workflow=self):
            ctype = wmr.content_type
            # We have also to check whether the global workflow is not
            # overwritten.
            for obj in ctype.model_class().objects.all():
                if utils.get_workflow(obj) == self:
                    objs.append(obj)

        # Get all objects whose local workflow this workflow
        for wor in WorkflowObjectRelation.objects.filter(workflow=self):
            if wor.content not in objs:
                objs.append(wor.content)

        return objs

    #FIXME: rename to something more approapriate (like ``set_to``)
    def set_to(self, ctype_or_obj):
        """
        Sets the workflow to passed content type or object. See the specific
        methods for more information.

        **Parameters:**

        ctype_or_obj
            The content type or the object to which the workflow should be set.
            Can be either a ContentType instance or any Django model instance.
            
        """
        if isinstance(ctype_or_obj, ContentType):
            return self.set_to_model(ctype_or_obj)
        else:
            return self.set_to_object(ctype_or_obj)

    #FIXME: rename to something more approapriate (like ``set_for_model``)
    def set_to_model(self, ctype):
        """
        Sets the workflow to the passed content type. If the content
        type has already an assigned workflow the workflow is overwritten.

        **Parameters:**

        ctype
            The content type which gets the workflow. Can be any Django model
            instance.            
        """
        
        try:
            wor = WorkflowModelRelation.objects.get(content_type=ctype)
        except WorkflowModelRelation.DoesNotExist:
            WorkflowModelRelation.objects.create(content_type=ctype, workflow=self)
        else:
            wor.workflow = self
            wor.save()
    
    #FIXME: rename to something more approapriate (like ``set_for_object``)
    def set_to_object(self, obj):
        """
        Sets the workflow to the passed object.

        If the object has already the given workflow nothing happens. Otherwise
        the workflow is set to the objectthe state is set to the workflow's
        initial state.

        **Parameters:**

        obj
            The object which gets the workflow.            
        """
        
        from dynflows import utils
        
        ctype = ContentType.objects.get_for_model(obj)
        try:
            wor = WorkflowObjectRelation.objects.get(content_type=ctype, content_id=obj.id)
        except WorkflowObjectRelation.DoesNotExist:
            WorkflowObjectRelation.objects.create(content = obj, workflow=self)
            utils.set_state(obj, self.initial_state)
        else:
            if wor.workflow != self:
                wor.workflow = self
                wor.save()
                utils.set_state(self.initial_state)


class State(models.Model):
    """
    A certain state within workflow.

    **Attributes:**

    name
        The unique name of the state within the workflow.

    workflow
        The workflow to which the state belongs.

    transitions
        The transitions of a workflow state.
    """
    
    name = models.CharField(_(u"Name"), max_length=100)
    workflow = models.ForeignKey(Workflow, verbose_name=_(u"Workflow"), related_name="states")
    transitions = models.ManyToManyField("Transition", verbose_name=_(u"Transitions"), blank=True, null=True, related_name="states")

    class Meta:
        ordering = ("name", )

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.workflow.name)

    def get_allowed_transitions(self, obj, user):
        """
        Given an object ``obj``, returns the list of all the transitions
        from this state the user ``user`` is allowed to trigger.   
        
        By definition, the return value of this method is a (possibly empty) subset
        of the set of available transitions from this state to any other state, 
        as defined by the workflow associated with the object itself.
        
        Permission checks are delegated to specific model instances: to define 
        a policy for a given transition, implement a method named ``transition.permission_name``
        within the model class of the instance.  If a suitable method is not found,
        the access control check is considered successful.        
        """
        #FIXME: what happens if ``self`` is not a state belonging to the ``obj``'s workflow ?
        allowed_transitions = []
        for transition in self.transitions.all():
            if transition.perm_name:
                try:
                    # retrieve the method (on the ``obj`` model class) defining 
                    # the access control policy for this transition  
                    perm_checker = getattr(obj, transition.perm_name)
                    # ``perm_checker`` should be a bound instance method of ``obj``
                    if not perm_checker(user):
                        continue
                except NameError:
                    # the model class of which ``obj`` is an instance doesn't define
                    # a checker for this permission, so we assume that everybody 
                    # is allowed to trigger it
                    pass
        
                # if the transition hasn't a permission associated with it,  
                # everybody is allowed to trigger it        
                allowed_transitions.append(transition) 
                
        return allowed_transitions                 


class Transition(models.Model):
    """
    A transition from a source to a destination state. The transition can
    be used from several source states.

    **Attributes:**

    name
        The unique name of the transition within a workflow.

    workflow
        The workflow to which the transition belongs. Must be a Workflow
        instance.

    destination
        The state after a transition has been processed. Must be a State
        instance.

    condition
        The condition when the transition is available. Can be any python
        expression.
    """
 
    name = models.CharField(_(u"Name"), max_length=100)
    workflow = models.ForeignKey(Workflow, verbose_name=_(u"Workflow"), related_name="transitions")
    destination = models.ForeignKey(State, verbose_name=_(u"Destination"), null=True, blank=True, related_name="destination_state")
    condition = models.CharField(_(u"Condition"), blank=True, max_length=100)
    # FIXME: add a sanity check: field's value should be a valid Python identifier
    # perhaps a custom field with a suitable validator could do the trick
    perm_name = models.CharField(_(u"Permission name"), blank=True, max_length=100, help_text=_('The name of the permission required to trigger this transition; must be a valid Python identifier.'))

    def __unicode__(self):
        return self.name

class StateObjectRelation(models.Model):
    """
    Stores the workflow state of an object.

    Provides a way to give any object a workflow state without changing the
    object's model.

    **Attributes:**

    content
        The object for which the state is stored. This can be any instance of
        a Django model.

    state
        The state of content. This must be a State instance.        
    """
    
    content_type = models.ForeignKey(ContentType, verbose_name=_(u"Content type"), related_name="state_object", blank=True, null=True)
    content_id = models.PositiveIntegerField(_(u"Content id"), blank=True, null=True)
    content = generic.GenericForeignKey(ct_field="content_type", fk_field="content_id")
    state = models.ForeignKey(State, verbose_name = _(u"State"))

    def __unicode__(self):
        return "%s %s - %s" % (self.content_type.name, self.content_id, self.state.name)

    class Meta:
        unique_together = ("content_type", "content_id", "state")

class WorkflowObjectRelation(models.Model):
    """
    Stores a workflow of an object.

    Provides a way to give any object a workflow without changing the object's
    model.

    **Attributes:**

    content
        The object for which the workflow is stored. This can be any instance of
        a Django model.

    workflow
        The workflow which is assigned to an object. This needs to be a workflow
        instance.        
    """
    
    content_type = models.ForeignKey(ContentType, verbose_name=_(u"Content type"), related_name="workflow_object", blank=True, null=True)
    content_id = models.PositiveIntegerField(_(u"Content id"), blank=True, null=True)
    content = generic.GenericForeignKey(ct_field="content_type", fk_field="content_id")
    workflow = models.ForeignKey(Workflow, verbose_name=_(u"Workflow"), related_name="wors")

    class Meta:
        unique_together = ("content_type", "content_id")

    def __unicode__(self):
        return "%s %s - %s" % (self.content_type.name, self.content_id, self.workflow.name)

class WorkflowModelRelation(models.Model):
    """
    Stores a workflow for a model (ContentType).

    Provides a way to give any object a workflow without changing the model.

    **Attributes:**

    Content Type
        The content type for which the workflow is stored. This can be any
        instance of a Django model.

    workflow
        The workflow which is assigned to an object. This needs to be a
        workflow instance.
    """
    
    content_type = models.ForeignKey(ContentType, verbose_name=_(u"Content Type"), unique=True)
    workflow = models.ForeignKey(Workflow, verbose_name=_(u"Workflow"), related_name="wmrs")

    def __unicode__(self):
        return "%s - %s" % (self.content_type.name, self.workflow.name)