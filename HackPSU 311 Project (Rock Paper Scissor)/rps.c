#include "rps.h"

#include <stdio.h>      // For printf in helper functions
#include <stdlib.h>     // For rand(), srand()
#include <time.h>       // For time()

// rps_seed()
// Seed the random number generator using current epoch time.
// We only need to do this ONCE per program run to avoid repeating sequences.
// GeeksforGeeks also seeds with time to ensure new randomness each run. :contentReference[oaicite:5]{index=5}
void rps_seed(void) {
    srand((unsigned int) time(NULL));    // Call srand(...) so that rand() gives different sequences
}

// rps_random_move()
// Return a random move for the CPU by using rand() % 3.
// rand() returns some large integer >= 0. Taking modulo 3
// forces it into {0,1,2}, which we map to ROCK/PAPER/SCISSORS.
rps_move_t rps_random_move(void) {
    int r = rand() % 3;                  // Generate pseudo-random int 0..2
    if (r == 0) {                         // If r == 0, CPU chose ROCK
        return RPS_ROCK;
    } else if (r == 1) {                  // If r == 1, CPU chose PAPER
        return RPS_PAPER;
    } else {                              // Else r == 2, CPU chose SCISSORS
        return RPS_SCISSORS;
    }
}

// rps_judge()
// Decide outcome using standard rules:
//
// Rock vs Paper    -> Paper wins
// Rock vs Scissors -> Rock wins
// Paper vs Scissors-> Scissors wins
// Same move        -> Tie
//
// We check tie first. Then we check all "player wins" cases.
// Otherwise CPU wins.
rps_result_t rps_judge(rps_move_t player, rps_move_t cpu) {
    // If moves are identical, it's a tie
    if (player == cpu) {
        return RPS_RESULT_TIE;
    }

    // Check all cases where the PLAYER wins.
    // Player ROCK beats CPU SCISSORS.
    if (player == RPS_ROCK && cpu == RPS_SCISSORS) {
        return RPS_RESULT_PLAYER_WIN;
    }

    // Player PAPER beats CPU ROCK.
    if (player == RPS_PAPER && cpu == RPS_ROCK) {
        return RPS_RESULT_PLAYER_WIN;
    }

    // Player SCISSORS beats CPU PAPER.
    if (player == RPS_SCISSORS && cpu == RPS_PAPER) {
        return RPS_RESULT_PLAYER_WIN;
    }

    // If it's not tie and not player win, then CPU wins.
    return RPS_RESULT_CPU_WIN;
}

// rps_play_round()
// This is a convenience wrapper for UI code.
// We take the player's move as an integer, convert it to rps_move_t,
// generate a CPU move, judge the round, and populate *out_round.
void rps_play_round(int32_t player_move, rps_round_t *out_round) {
    // Store the player's move into the struct
    out_round->player_move = (rps_move_t) player_move;

    // Generate a random move for the CPU
    out_round->cpu_move = rps_random_move();

    // Decide who wins
    out_round->result = rps_judge(out_round->player_move, out_round->cpu_move);
}

// rps_move_to_string()
// Convert enum move to a friendly string for printing.
const char *rps_move_to_string(rps_move_t move) {
    if (move == RPS_ROCK) {
        return "ROCK";
    } else if (move == RPS_PAPER) {
        return "PAPER";
    } else if (move == RPS_SCISSORS) {
        return "SCISSORS";
    } else {
        return "UNKNOWN";
    }
}

// rps_result_to_string()
// Convert enum result to a friendly summary.
const char *rps_result_to_string(rps_result_t result) {
    if (result == RPS_RESULT_TIE) {
        return "It's a TIE.";
    } else if (result == RPS_RESULT_PLAYER_WIN) {
        return "You WIN!";
    } else if (result == RPS_RESULT_CPU_WIN) {
        return "Computer WINS!";
    } else {
        return "Unknown result.";
    }
}
