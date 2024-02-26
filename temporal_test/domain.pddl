
(define (domain Quantum)
    (:requirements :strips :typing :durative-actions)
    (:types
        pqubit gate depth - object
        lqubit - gate
    )
    (:constants
        l0 l1 l2 l3 - lqubit
        g0 g1 g2 g3 - gate
    )
    (:predicates
        (occupied ?p - pqubit)
        (mapped ?l - lqubit ?p - pqubit)
        (connected ?p1 ?p2 - pqubit)
        (done ?g - gate)
        (free ?l - lqubit)
    )
    
    (:durative-action swap
        :parameters (?l1 ?l2 - lqubit ?p1 ?p2 - pqubit)
        :duration (= ?duration 4)
        :condition (and 
            (at start (and 
                (mapped ?l1 ?p1) (mapped ?l2 ?p2)
                (connected ?p1 ?p2) 
                (free ?l1) (free ?l2)
            ))
        )
        :effect (and 
            (at start (and 
                (not (free ?l1)) (not (free ?l2))
            ))
            (at end (and 
                (not (mapped ?l1 ?p1)) (not (mapped ?l2 ?p2)) 
                (mapped ?l1 ?p2) (mapped ?l2 ?p1) 
                (free ?l1) (free ?l2)
            ))
        )
    )

    (:durative-action apply_gate_g0
        :parameters (?p - pqubit)
        :duration (= ?duration 2)
        :condition (and 
            (at start (and 
                (not (done g0))
                (not (occupied ?p))
                (free l0)
            ))
        )
        :effect (and 
            (at start (and 
                (not (free l0))
            ))
            (at end (and 
                (done g0)
                (occupied ?p)
                (mapped l0 ?p)
                (free l0)
            ))
        )
    )
    
    (:durative-action apply_cx_g1
        :parameters (?p1 ?p2 - pqubit)
        :duration (= ?duration 2)
        :condition (and 
            (at start (and 
                (not (done g1))
                (connected ?p1 ?p2) 
                (not (occupied ?p1)) (not (occupied ?p2))
                (free l2) (free l3)
            ))
        )
        :effect (and 
            (at start (and 
                (not (free l2)) (not (free l3))
            ))
            (at end (and 
                (done g1)
                (occupied ?p1) (occupied ?p2)
                (mapped l2 ?p1) (mapped l3 ?p2)
                (free l2) (free l3)
            ))
        )
    )
    
    (:durative-action apply_cx_g2
        :parameters (?p1 ?p2 - pqubit)
        :duration (= ?duration 2)
        :condition (and 
            (at start (and 
                (not (done g2)) (done g0) 
                (connected ?p1 ?p2)  
                (mapped l0 ?p1) (not (occupied ?p2))
                (free l0) (free l1)
            ))
        )
        :effect (and 
            (at start (and 
                (not (free l0)) (not (free l1))
            ))
            (at end (and 
                (done g2) (occupied ?p2) (mapped l1 ?p2)
                (free l0) (free l1)
            ))
        )
    )
    
    (:durative-action apply_gate_g3
        :parameters (?p - pqubit)
        :duration (= ?duration 2)
        :condition (and 
            (at start (and 
                (not (done g3)) (done g1)
                (mapped l2 ?p)
                (free l2)
            ))
        )
        :effect (and 
            (at start (and 
                (not (free l2))
            ))
            (at end (and 
                (done g3)
                (free l2)
            ))
        )
    )
)
