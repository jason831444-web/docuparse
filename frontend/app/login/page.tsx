"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-background px-6 py-12">
      <div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="flex flex-col justify-center">
          <p className="text-sm font-medium text-primary">DocuParse</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-normal">Welcome back to your document workflow.</h1>
          <p className="mt-4 max-w-xl text-muted-foreground">
            Review incoming documents, clear your needs-review queue, and keep the library organized by meaning instead of file clutter.
          </p>
        </section>
        <Card className="border-border/80 bg-white">
          <CardHeader>
            <CardTitle>Log in</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="grid gap-2 text-sm font-medium">
              Email
              <Input type="email" placeholder="you@company.com" />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              Password
              <Input type="password" placeholder="Enter your password" />
            </label>
            <Button className="w-full">Continue</Button>
            <p className="text-sm text-muted-foreground">
              New here?{" "}
              <Link href="/signup" className="text-foreground underline-offset-4 hover:underline">
                Create an account
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
