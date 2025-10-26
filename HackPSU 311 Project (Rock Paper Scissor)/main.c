#include "rps.h"
#include <stdio.h>   // For printf / scanf
#include <stdlib.h>  // For exit()

int main(void) {
    // Call rps_seed() exactly once.
    // This mirrors the GeeksforGeeks idea that you seed the RNG so that
    // rand() will generate different outcomes each run. :contentReference[oaicite:6]{index=6}
    rps_seed();

    while (1) {
        int user_choice = -1;

        printf("\nRock Paper Scissors\n");
        printf("Enter your move:\n");
        printf(" 0 = ROCK\n 1 = PAPER\n 2 = SCISSORS\n 9 = quit\n> ");

        if (scanf("%d", &user_choice) != 1) {
            // If scanf fails, exit.
            printf("Bad input, exiting.\n");
            break;
        }

        if (user_choice == 9) {
            printf("Goodbye!\n");
            break;
        }

        if (user_choice < 0 || user_choice > 2) {
            printf("Invalid choice. Please enter 0, 1, 2, or 9.\n");
            continue;
        }

        // Play one round using our library call
        rps_round_t round;
        rps_play_round(user_choice, &round);

        // Print what happened
        printf("You chose:      %s\n", rps_move_to_string(round.player_move));
        printf("Computer chose: %s\n", rps_move_to_string(round.cpu_move));
        printf("%s\n", rps_result_to_string(round.result));
    }

    return 0;
}
