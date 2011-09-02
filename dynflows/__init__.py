from dynflows import utils 

class WorkflowBase(object):
    """Mixin class to make objects workflow-aware. """
    
    # FIXME: use a property instead !
    def get_workflow(self):
        """
        Returns the current workflow of the object.
        """
        
        return utils.get_workflow(self)

    # FIXME: use a property instead !
    def remove_workflow(self):
        """
        Removes the workflow from the object. After this function has been
        called the object has no *own* workflow anymore (it might have one via
        its content type).
        """
        
        return utils.remove_workflow_from_object(self)
    
    # FIXME: use a property instead !
    def set_workflow(self, workflow):
        """
        Sets the passed workflow to the object. This will set the local
        workflow for the object.

        If the object has already the given workflow nothing happens.
        Otherwise the object gets the passed workflow and the state is set to
        the workflow's initial state.

        **Parameters:**

        workflow
            The workflow which should be set to the object. Can be a Workflow
            instance or a string with the workflow name.
        obj
            The object which gets the passed workflow.
        """
        
        return utils.set_workflow_for_object(self, workflow)

    # FIXME: use a property instead !
    def get_state(self):
        """
        Returns the current workflow state of the object. 
        """
                
        return utils.get_state(self)

    # FIXME: use a property instead !
    def set_state(self, state):
        """
        Sets the workflow state of the object.
        """
        
        return utils.set_state(self, state)
    
    # FIXME: use a property instead !
    def set_initial_state(self):
        """
        Sets the initial state of the current workflow to the object.
        """
        return self.set_state(self.get_workflow().initial_state)
    
    # FIXME: use a property instead !
    def get_allowed_transitions(self, user):
        """
        Returns allowed transitions for the current state.
        """
        return utils.get_allowed_transitions(self, user)
    
    
    def do_transition(self, transition, user):
        """
        Processes the passed transition (if allowed).
        """
        
        return utils.do_transition(self, transition, user)