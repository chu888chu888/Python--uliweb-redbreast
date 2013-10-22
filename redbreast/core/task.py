import logging

from redbreast.core import WFException
from redbreast.core.spec import *
from uuid import uuid4
import time

LOG = logging.getLogger(__name__)

class Task(object):

    WAITING   =  1
    READY     =  2
    EXECUTING =  4
    EXECUTED  =  8
    COMPLETED = 16
    
    # waiting --> ready()  --> ready
    # ready --> execute() 
    # if async ---> executing
    #    async-callback --> executed
    # if sync --> executed --> route() --> completed
    # executed --> transfer() ---> completed

    state_names = {
        WAITING:   'WAITING',
        READY:     'READY',
        EXECUTING: 'EXECUTING',
        EXECUTED:  'EXECUTED',
        COMPLETED: 'COMPLETED',
    }
    
    state_fire_event_names = {
        WAITING:   'enter',
        READY:     'ready',
        EXECUTING: 'executing',
        EXECUTED:  'executed',
        COMPLETED: 'completed',
    }
    
    class Iterator(object):
        def __init__(self, current, filter=None):
            self.filter = filter
            self.path = [current]
    
        def __iter__(self):
            return self
    
        def _next(self):
            if len(self.path) == 0:
                raise StopIteration()
            
            current = self.path[-1]
            if current.children:
                self.path.append(current.children[0])
                 
                if self.filter is not None and current.state & self.filter == 0:
                    return None
                return current
            
            while True:
                
                old_child = self.path.pop(-1)
                
                if len(self.path) == 0:
                    break;
                
                parent = self.path[-1]
                pos = parent.children.index(old_child)
                if len(parent.children) > (pos + 1):
                    self.path.append(parent.children[pos + 1])
                    break
            
            if self.filter is not None and current.state & self.filter == 0:
                return None
            
            return current
    
        def next(self):
            while True:
                next = self._next()
                if next is not None:
                    return next
    
    
    def __init__(self, workflow, task_spec, parent=None, state=WAITING):
        self.workflow = workflow
        self.spec = task_spec
        self.parents = []
        if parent:
            self.parents.append(parent)
            
        self._state = None
        self.state_history = []
        self.state = state
        
        self.data = {}
        self.id = uuid4()
        
        self.children = []
        if parent is not None:
            for p in self.parents:
                p.add_child(self)
            
    def __iter__(self):
        return Task.Iterator(self)
            
    def _getstate(self):
        return self._state
    
    def _setstate(self, value):
        if self._state == value:
            return
        old = self.get_state_name()
        self._state = value
        self.state_history.append(value)
        self.last_state_change = time.time()
        
        map = {}
        
        #pubsub
        event_type = self.state_fire_event_names.get(self.state, None)
        
        if event_type:
            self.workflow.spec.fire(event_type, task=self, workflow=self.workflow)
            self.workflow.fire(event_type, task=self, workflow=self.workflow)
            self.workflow.fire("state_changed", task=self, workflow=self.workflow)
        
        LOG.debug("Moving '%s' from %s to %s" % 
            (self.get_name(), old, self.get_state_name()))
            
    def _delstate(self):
        del self._state
    
    state = property(_getstate, _setstate, _delstate, "State property.")
        
    def get_level(self):
        level = 0
        task = self.parent
        while task is not None:
            level += 1
            task = task.parent
        return level
    
    def get_state_name(self):
        return self.state_names.get(self.state, None)
    
    def get_name(self):
        return self.spec.name
    
    def get_spec_name(self):
        return self.spec.get_spec_name()

    def add_parent(self, parent):
        self.parents.append(parent)
            
    def add_child(self, child):
        self.children.append(child)
        self.workflow.fire("trans:add", from_task=self, to_task=child, workflow=self.workflow,)

    def remove_parent(self, parent):
        self.parents.remove(parent)
        
    def remove_child(self, child):
        self.children.remove(child)
        
    def kill(self):
        for p in self.parents:
            p.remove_child(self)
        self.parents = []
        
    def is_ready(self):
        return self.spec.is_ready(self, self.workflow)
    
    def do_execute(self, transfer=False):
        return self.spec.do_execute(self, self.workflow, transfer=transfer)
    
    def is_descendant_of(self, parent):
        if not self.parents:
            return False
        for p in self.parents:
            if self.parent == p:
                return True
            
        for p in self.parents:
            if p.is_descendant_of(parent):
                return True
    
    def find(self, task_spec):
        if self.spec == task_spec:
            return self
        for child in self:
            if child.spec != task_spec:
                continue
            return child
        return None

    def __repr__(self):
        return '<Task (%s) in state %s at %s>' % (
            self.spec.name,
            self.get_state_name(),
            hex(id(self)))
    
    def get_dump(self, indent=0, recursive=True):
        dbg  = (' ' * indent * 2)
        dbg += ' %s '   % (self.get_name())
        dbg += ' (%s)'    % self.get_state_name()
        dbg += ' Children: %s' % len(self.children)
        if recursive:
            for child in self.children:
                dbg += '\n' + child.get_dump(indent + 1)
        return dbg
    
    def dump(self, indent=0):
        print self.get_dump()
                    
