
(define (domain Quantum)
  (:requirements :typing :strips :negative-preconditions)
  (:types
    pqubit gate depth - object
    lqubit - gate
  )
  (:constants
    l1 l2 l3 l4 - lqubit
    g1 g2 g3 g4 - gate
    d0 d1 d2 d3 d4 d5 d6 - depth ;; we must define all depths until a chosen max depth
    )
  (:predicates
    (occupied ?p - pqubit)
    (mapped ?l - lqubit ?p - pqubit)
    (connected ?p1 ?p2 - pqubit)
    (done ?g - gate)
    (clock ?p - pqubit ?d - depth)
    (next_depth ?d1 ?d2 - depth)
    (next_swap_depth ?d1 ?d2 - depth)
    (is_swapping1 ?p1 ?p2 - pqubit)
    (is_swapping2 ?p1 ?p2 - pqubit)
    (is_swapping ?p - pqubit)
  )
  (:action swap
    :parameters (?l1 ?l2 - lqubit ?p1 ?p2 - pqubit ?d1 ?d2 - depth)
    :precondition (and (mapped ?l1 ?p1) (mapped ?l2 ?p2) (connected ?p1 ?p2) (next_swap_depth ?d1 ?d2) (clock ?p1 ?d1) (clock ?p2 ?d1))
    :effect (and (not(mapped ?l1 ?p1)) (not(mapped ?l2 ?p2)) (mapped ?l1 ?p2) (mapped ?l2 ?p1) (not(clock ?p1 ?d1)) (not(clock ?p2 ?d1)) (clock ?p1 ?d2) (clock ?p2 ?d2) (is_swapping1 ?p1 ?p2) (is_swapping ?p1) (is_swapping ?p2))
  )
  (:action swap_dummy1
    :parameters (?p1 ?p2 - pqubit)
    :precondition (is_swapping1 ?p1 ?p2)
    :effect (and (not (is_swapping1 ?p1 ?p2)) (is_swapping2 ?p1 ?p2))
  )
  (:action swap_dummy2
    :parameters (?p1 ?p2 - pqubit)
    :precondition (and (is_swapping2 ?p1 ?p2))
    :effect (and (not (is_swapping2 ?p1 ?p2)) (not (is_swapping ?p1)) (not (is_swapping ?p2)))
  )
  (:action apply_gate_g1
    :parameters (?p - pqubit ?d1 ?d2 - depth)
    :precondition (and (not(done g1)) (not (occupied ?p)) (next_depth ?d1 ?d2) (clock ?p ?d1) (not (is_swapping ?p)))
    :effect (and (done g1) (mapped l1 ?p) (occupied ?p) (clock ?p ?d2) (not(clock ?p ?d1)))
  )
  (:action apply_cnot_g2
    :parameters (?p1 ?p2 - pqubit ?d1 ?d2 - depth)
    :precondition (and (not(done g2)) (connected ?p1 ?p2) (done g1) (mapped l1 ?p1) (not (occupied ?p2)) (next_depth ?d1 ?d2) (clock ?p1 ?d1) (clock ?p2 ?d1) (not (is_swapping ?p1)) (not (is_swapping ?p2)))
    :effect (and (done g2) (mapped l2 ?p2) (occupied ?p2) (clock ?p1 ?d2) (not(clock ?p1 ?d1)) (clock ?p2 ?d2) (not(clock ?p2 ?d1)))
  )
  (:action apply_cnot_g3
    :parameters (?p1 ?p2 - pqubit ?d1 ?d2 - depth)
    :precondition (and (not(done g3)) (connected ?p1 ?p2) (next_depth ?d1 ?d2) (not (occupied ?p1)) (not (occupied ?p2)) (clock ?p1 ?d1) (clock ?p2 ?d1) (not (is_swapping ?p1)) (not (is_swapping ?p2)))
    :effect (and (done g3) (mapped l3 ?p1) (occupied ?p1) (mapped l4 ?p2) (occupied ?p2) (clock ?p1 ?d2) (not(clock ?p1 ?d1)) (clock ?p2 ?d2) (not(clock ?p2 ?d1)))
  )
  (:action apply_gate_g4
    :parameters (?p - pqubit ?d1 ?d2 - depth)
    :precondition (and (not(done g4)) (done g3) (mapped l3 ?p) (next_depth ?d1 ?d2) (clock ?p ?d1) (not (is_swapping ?p)))
    :effect (and (done g4) (clock ?p ?d2) (not(clock ?p ?d1)))
  )
  (:action nop
    :parameters (?p - pqubit ?d1 ?d2 - depth)
    :precondition (and (next_depth ?d1 ?d2) (clock ?p ?d1) (not (is_swapping ?p)))
    :effect (and (clock ?p ?d2) (not(clock ?p ?d1)))
  )
)