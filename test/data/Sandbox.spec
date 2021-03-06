task TaskStart:
    class : redbreast.core.spec.SimpleTask
end

task TaskA:
    class : redbreast.core.spec.ChoiceTask
end

task TaskB:
    class : redbreast.core.spec.SimpleTask
end

task TaskC(TaskB):
end

task TaskD(TaskB):
    default: True
end

task TaskE(TaskB):
end

task TaskF(TaskB):
end

task TaskG:
    class : redbreast.core.spec.JoinTask
end

task TaskH:
    class : redbreast.core.spec.SimpleTask
end



process TestWorkflow:
    '''
    desc This is a small workflow definination for testing.
    '''
    key : value
    
    tasks:
        TaskStart as start1
        TaskStart as start2
        TaskA as A
        TaskB as B
        TaskC as C
        TaskD as D
        TaskE as E
        TaskF as F
        TaskG as G
        TaskH as H
    end
    
    flows:
        start1->A->B->C->G->H
        A->D->E->F->G
    end
    
    code A.ready:
        print task, " go to ready"
        return YES
    end
    
    code B.ready:
        return True
    end
end
