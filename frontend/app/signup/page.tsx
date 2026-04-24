"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function SignupPage() {
  return (
    <main className="min-h-screen bg-background px-6 py-12">
      <div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="flex flex-col justify-center">
          <p className="text-sm font-medium text-primary">Launch-ready workflow</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-normal">Create your DocuParse workspace.</h1>
          <p className="mt-4 max-w-xl text-muted-foreground">
            Upload documents, organize them automatically into AI folders, and keep review, confirmation, and reprocessing in one tidy loop.
          </p>
        </section>
        <Card className="border-border/80 bg-white">
          <CardHeader>
            <CardTitle>Sign up</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="grid gap-2 text-sm font-medium">
              Full name
              <Input placeholder="Your name" />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              Email
              <Input type="email" placeholder="you@company.com" />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              Password
              <Input type="password" placeholder="Create a password" />
            </label>
            <Button className="w-full">Create account</Button>
            <p className="text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link href="/login" className="text-foreground underline-offset-4 hover:underline">
                Log in
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
