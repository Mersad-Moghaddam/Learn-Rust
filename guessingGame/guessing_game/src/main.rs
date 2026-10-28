use std::io;
use rand::prelude::*;
use std::cmp::Ordering;


fn main() {
    println!("Guess the Number!");
    let secret_number = rand::rng().random_range(1..=100);
    println!("the secret number is: {secret_number}");
    loop {
        println!("Please input youre guess.");

        let mut guess = String::new();

        io::stdin()
            .read_line(&mut guess)
            .expect("failed to read line");

        let guess: u32 = match guess.trim().parse() {
            Ok(num) => num,
            Err(_) => continue,
        };

        println!("You guessed: {guess}");

        match guess.cmp(&secret_number) {
            Ordering::Less => println!("Too Small!"),
            Ordering::Greater => println!("Too big!"),
            Ordering::Equal => {
                println!("You Win");
                break;
            }
        }
    }
}
