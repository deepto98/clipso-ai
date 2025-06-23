import React from 'react'
import { cn } from '@/lib/utils'

interface PageHeadingProps {
  title: string
  description?: string
  className?: string
  descriptionClassName?: string
}

const PageHeading = ({
  title,
  description,
  className,
  descriptionClassName,
}: PageHeadingProps) => {
  return (
    <div className={cn('text-center mb-6 pt-2 md:pt-4', className)}>
      <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-transparent bg-clip-text">
        {title}
      </h1>
      {description && (
        <p className={cn('text-muted-foreground', descriptionClassName)}>
          {description}
        </p>
      )}
    </div>
  )
}

export default PageHeading