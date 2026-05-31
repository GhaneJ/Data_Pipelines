export const MIN_MANAGED_PASSWORD_LENGTH = 10;

export interface PasswordPolicyResult {
  isValid: boolean;
  checks: { label: string; passed: boolean }[];
}

export function getPasswordPolicy(password: string): PasswordPolicyResult {
  const checks = [
    { label: `At least ${MIN_MANAGED_PASSWORD_LENGTH} characters`, passed: password.length >= MIN_MANAGED_PASSWORD_LENGTH },
    { label: "Uppercase letter", passed: /[A-Z]/.test(password) },
    { label: "Lowercase letter", passed: /[a-z]/.test(password) },
    { label: "Digit", passed: /\d/.test(password) },
    { label: "Special character", passed: /[^A-Za-z0-9]/.test(password) },
  ];

  return {
    isValid: checks.every((check) => check.passed),
    checks,
  };
}

export function passwordPolicyMessage(): string {
  return `Password must be at least ${MIN_MANAGED_PASSWORD_LENGTH} characters and include uppercase, lowercase, digit, and special character.`;
}
