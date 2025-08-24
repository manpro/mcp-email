import * as React from "react"
import { cn } from "@/lib/utils"

interface TooltipProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'content'> {
  content: React.ReactNode
  children: React.ReactNode
}

const Tooltip = React.forwardRef<HTMLDivElement, TooltipProps>(
  ({ className, content, children, ...props }, ref) => {
    const [isVisible, setIsVisible] = React.useState(false)

    return (
      <div
        ref={ref}
        className="relative inline-block"
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        {...props}
      >
        {children}
        {isVisible && (
          <div
            className={cn(
              "absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 rounded-md bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md border animate-in fade-in-0 zoom-in-95",
              className
            )}
          >
            {content}
            <div className="absolute top-full left-1/2 h-0 w-0 -translate-x-1/2 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-popover" />
          </div>
        )}
      </div>
    )
  }
)
Tooltip.displayName = "Tooltip"

export { Tooltip }