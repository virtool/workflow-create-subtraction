use std::fs::File;
use std::io::{self, BufRead};
use std::path::Path;
use pyo3::prelude::*;

#[pymodule]
fn count_nucleotides_and_seqs(_py: Python, m: &PyModule) -> Result<(), PyErr>
{
    m.add_function(wrap_pyfunction!(run, m)?)?;
    return Ok(());
}

#[pyfunction]
fn run(filename: String) -> (u64, u64, u64, u64, u64, u32)
{

    let mut a: u64 = 0;
    let mut t: u64 = 0;
    let mut g: u64 = 0;
    let mut c: u64 = 0;
    let mut n: u64 = 0;

    let mut count: u32 = 0;

    if let Ok(lines) = read_lines(filename) {
        for line in lines {
            if let Ok(fasta_line) = line {
                if fasta_line.starts_with('>') {
                    count = count + 1;
                    continue;
                }

                for letter in fasta_line.chars() {
                    match letter {
                        'a' | 'A' => a = a + 1,
                        't' | 'T' => t = t + 1,
                        'g' | 'G' => g = g + 1,
                        'c' | 'C' => c = c + 1,
                        'n' | 'N' => n = n + 1,
                        _ => continue,
                    }
                }
            }
        }
    }

    return (a, t, g, c, n, count);
}

fn read_lines<P>(filename: P) -> io::Result<io::Lines<io::BufReader<File>>>
where
    P: AsRef<Path>,
{
    let file = File::open(filename)?;
    Ok(io::BufReader::new(file).lines())
}
