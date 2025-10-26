#ifndef RPS_H
#define RPS_H

#include <stdbool.h>   // For bool type
#include <stdint.h>    // For fixed-width ints like int32_t

// Enumerated type for possible moves in Rock-Paper-Scissors.
// We assign explicit integer values so they are stable across C and Python.
typedef enum {
    RPS_ROCK = 0,      // Rock choice, stored as integer 0
    RPS_PAPER = 1,     // Paper choice, stored as integer 1
    RPS_SCISSORS = 2   // Scissors choice, stored as integer 2
} rps_move_t;

// Enumerated type for round outcome.
// We define who won the round.
typedef enum {
    RPS_RESULT_TIE = 0,        // Both moves were the same
    RPS_RESULT_PLAYER_WIN = 1, // Player beats CPU
    RPS_RESULT_CPU_WIN = 2     // CPU beats Player
} rps_result_t;

// This struct holds the full outcome of a single round.
// We will also mirror this exact memory layout in Python's ctypes.Structure.
typedef struct {
    rps_move_t player_move;   // The player's move for this round
    rps_move_t cpu_move;      // The computer's randomly generated move
    rps_result_t result;      // The result of the round
} rps_round_t;

// rps_seed()
// This function initializes the pseudo-random number generator using the
// current time. Calling srand(time(NULL)) once per run means the computer's
// move will look different each time the program starts, instead of repeating
// the same pattern every run. GeeksforGeeks also seeds the RNG before using rand(). :contentReference[oaicite:3]{index=3}
void rps_seed(void);

// rps_random_move()
// This function returns a random move for the CPU by generating an integer
// in {0,1,2} and mapping 0->ROCK, 1->PAPER, 2->SCISSORS. This mirrors the
// "computer picks randomly" behavior described on GeeksforGeeks. :contentReference[oaicite:4]{index=4}
rps_move_t rps_random_move(void);

// rps_judge(player, cpu)
// This function applies standard RPS rules to decide who won the round.
// It returns RPS_RESULT_PLAYER_WIN, RPS_RESULT_CPU_WIN, or RPS_RESULT_TIE.
rps_result_t rps_judge(rps_move_t player, rps_move_t cpu);

// rps_play_round(player_move, out_round)
// High-level helper: given the player's move (0,1,2), it will:
//   1. generate a CPU move,
//   2. compute the result,
//   3. fill the rps_round_t struct pointed to by out_round.
void rps_play_round(int32_t player_move, rps_round_t *out_round);

// (Optional utility for CLI only, not strictly needed by Python)
// These turn enum values into human-readable strings.
const char *rps_move_to_string(rps_move_t move);
const char *rps_result_to_string(rps_result_t result);

#endif // RPS_H
