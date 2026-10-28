use std::io;


fn main() {
    println!("Guess the Number!");

    println!("Please input youre guess.");

    let mut guess = String::new();

    io::stdin()
        .read_line(&mut guess)
        .expect("failed to read line");

    println!("You guessed: {guess}");
}
