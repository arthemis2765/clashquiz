import { useEffect, useRef } from "react";

/**
 * Champ de réponse du jeu.
 * - Pas de majuscule automatique ni de correction du clavier mobile : la casse n'a pas d'importance
 *   (le serveur compare sans tenir compte des majuscules, accents et abréviations).
 * - `readOnly` garde le focus (le clavier mobile reste ouvert entre deux questions) ; `disabled` le retire.
 * - `focusKey` : à chaque changement (nouvelle question, nouveau tour), le champ reprend le focus.
 */
export default function AnswerInput({
  value,
  onChange,
  disabled = false,
  readOnly = false,
  placeholder,
  shake = false,
  maxLength = 200,
  focusKey,
}) {
  const inputRef = useRef(null);

  useEffect(() => {
    if (!disabled && !readOnly) inputRef.current?.focus();
  }, [focusKey, disabled, readOnly]);

  return (
    <input
      ref={inputRef}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      readOnly={readOnly}
      maxLength={maxLength}
      autoComplete="off"
      autoCorrect="off"
      autoCapitalize="none"
      spellCheck={false}
      className={`min-w-0 flex-1 px-3 sm:px-4 py-3 outline-none transition-transform ${shake ? "animate-shake" : ""}`}
      style={{
        background: "rgba(241,234,216,0.04)",
        border: shake ? "1px solid var(--coral)" : "1px solid var(--line-strong)",
        color: "var(--parchment)",
      }}
    />
  );
}
