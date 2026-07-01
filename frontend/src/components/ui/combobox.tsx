import * as React from "react";
import { cn } from "@/lib/utils";
import { Input } from "./input";

export interface ComboBoxOption {
  value: string;
  label: string;
}

interface ComboBoxProps {
  options: ComboBoxOption[];
  value: string;
  onChange: (value: string, option?: ComboBoxOption) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function ComboBox({
  options,
  value,
  onChange,
  placeholder,
  disabled,
  className,
}: ComboBoxProps) {
  const [open, setOpen] = React.useState(false);
  const [inputValue, setInputValue] = React.useState(value);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const listRef = React.useRef<HTMLUListElement>(null);
  const [activeIndex, setActiveIndex] = React.useState(-1);

  // 同步外部 value - 显示对应的label而不是value本身
  React.useEffect(() => {
    const option = options.find((o) => o.value === value);
    if (option) {
      setInputValue(option.label);
    } else if (value === "" || value === "0") {
      setInputValue("");
    } else {
      setInputValue(value);
    }
  }, [value, options]);

  // 点击外部关闭
  React.useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filtered = React.useMemo(() => {
    if (!inputValue.trim()) return options;
    const s = inputValue.trim().toLowerCase();
    return options.filter((o) => o.label.toLowerCase().includes(s));
  }, [options, inputValue]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setInputValue(v);
    setOpen(true);
    setActiveIndex(-1);
    // 如果没有精确匹配，只传文字
    const exact = options.find((o) => o.label === v);
    if (exact) {
      onChange(exact.value, exact);
    } else {
      onChange(v, undefined);
    }
  };

  const handleSelect = (option: ComboBoxOption) => {
    setInputValue(option.label);
    setOpen(false);
    setActiveIndex(-1);
    onChange(option.value, option);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      setOpen(false);
      setActiveIndex(-1);
      return;
    }
    if (!open) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        setOpen(true);
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) =>
        prev < filtered.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => (prev > 0 ? prev - 1 : -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < filtered.length) {
        handleSelect(filtered[activeIndex]);
      } else if (filtered.length > 0) {
        handleSelect(filtered[0]);
      }
    }
  };

  // activeIndex 变化时滚动到可视区域
  React.useEffect(() => {
    if (activeIndex >= 0 && listRef.current) {
      const activeItem = listRef.current.children[activeIndex] as HTMLElement;
      if (activeItem) {
        activeItem.scrollIntoView({ block: "nearest" });
      }
    }
  }, [activeIndex]);

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <Input
        value={inputValue}
        onChange={handleInputChange}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
      />
      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border border-input bg-popover text-popover-foreground shadow-md max-h-60 overflow-auto">
          {filtered.length > 0 ? (
            <ul ref={listRef} className="py-1">
              {filtered.map((option, idx) => (
                <li
                  key={option.value}
                  className={cn(
                    "px-3 py-2 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground",
                    idx === activeIndex && "bg-accent text-accent-foreground"
                  )}
                  onClick={() => handleSelect(option)}
                  onMouseEnter={() => setActiveIndex(idx)}
                >
                  {option.label}
                </li>
              ))}
            </ul>
          ) : (
            <div className="px-3 py-2 text-sm text-muted-foreground">
              {options.length === 0 ? "暂无选项" : "无匹配结果"}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
