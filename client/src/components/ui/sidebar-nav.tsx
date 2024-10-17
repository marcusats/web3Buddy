"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MotionProps, motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { buttonVariants } from "./button";


interface SidebarNavProps extends React.HTMLAttributes<HTMLElement> {
  items: {
    href: string;
    title: string;
  }[];
}

export function SidebarNav({ className, items, ...props }: SidebarNavProps) {
  const pathname = usePathname();

  // Animation variants for staggering the items
  const itemVariants = {
    hidden: { opacity: 0, x: -20 }, // Hidden state
    visible: { opacity: 1, x: 0 },  // Visible state
  };

  return (
    <motion.nav
      initial="hidden"
      animate="visible"
      transition={{ staggerChildren: 0.2 }} // Staggering animation between items
      className={cn("flex lg:flex-col lg:space-x-0 lg:space-y-1", className)}
      {...props as MotionProps}
    >
      {items.map((item, index) => (
        <motion.div key={item.href} variants={itemVariants}>
          <Link
            href={item.href}
            className={cn(
              buttonVariants({ variant: "ghost" }),
              pathname === item.href ? "bg-muted hover:bg-muted" : "hover:bg-transparent hover:underline text-[#edeaf7]",
              "justify-start"
            )}
          >
            {item.title}
          </Link>
        </motion.div>
      ))}
    </motion.nav>
  );
}
