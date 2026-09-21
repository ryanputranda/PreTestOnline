CREATE DATABASE IF NOT EXISTS ukdc_exam
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ukdc_exam;

CREATE TABLE IF NOT EXISTS questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_answer ENUM('A','B','C','D') NOT NULL,
    question_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_question_order (question_order, id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    participant_name VARCHAR(150) NOT NULL,
    test_date DATETIME NOT NULL,
    total_questions INT NOT NULL,
    correct_answers INT NOT NULL,
    incorrect_answers INT NOT NULL,
    final_score DECIMAL(6,2) NOT NULL,
    INDEX idx_test_date (test_date),
    INDEX idx_score (final_score)
) ENGINE=InnoDB;
