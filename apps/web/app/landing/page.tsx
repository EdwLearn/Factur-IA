"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Brain,
  Plug,
  Upload,
  CheckCircle,
  FolderSyncIcon as Sync,
  Star,
  ArrowRight,
  Play,
  Menu,
  X,
  FileText,
  Clock,
  TrendingUp,
  Phone,
  Mail,
  MapPin,
} from "lucide-react"
import Link from "next/link"

export default function LandingPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const features = [
    {
      icon: Brain,
      title: "Procesamiento Inteligente",
      description: "AWS Textract + Visión por Computadora para extraer datos con precisión del 95%+",
      color: "bg-blue-100 text-blue-600",
    },
    {
      icon: Sync,
      title: "Actualización Automática",
      description: "Inventario sincronizado en tiempo real sin intervención manual",
      color: "bg-green-100 text-green-600",
    },
    {
      icon: Plug,
      title: "Integración POS",
      description: "Conecta con Mayasis, Siigo y otros sistemas populares en Colombia",
      color: "bg-purple-100 text-purple-600",
    },
  ]

  const process = [
    {
      step: "01",
      title: "Sube tu factura",
      description: "Foto desde móvil o archivo PDF",
      icon: Upload,
    },
    {
      step: "02",
      title: "IA extrae los datos",
      description: "Automático en segundos",
      icon: Brain,
    },
    {
      step: "03",
      title: "Inventario actualizado",
      description: "Sincronización automática",
      icon: CheckCircle,
    },
  ]

  const testimonials = [
    {
      name: "María González",
      company: "Almacén Medellín JA",
      text: "FacturIA redujo el tiempo de procesamiento de facturas en un 90%. Ahora puedo enfocarme en atender clientes.",
      rating: 5,
    },
    {
      name: "Carlos Rodríguez",
      company: "Melos Paisas",
      text: "La integración con nuestro POS fue perfecta. El inventario se actualiza automáticamente.",
      rating: 5,
    },
    {
      name: "Ana Martínez",
      company: "Almacén El Rey",
      text: "Increíble precisión en la extracción de datos. Ya no tenemos errores de digitación.",
      rating: 5,
    },
  ]

  const pricing = [
    {
      name: "Básico",
      price: "Gratis",
      period: "",
      description: "Perfecto para empezar",
      features: ["5 facturas/mes", "Procesamiento básico", "Soporte por email", "Dashboard básico"],
      cta: "Comenzar Gratis",
      popular: false,
    },
    {
      name: "Pro",
      price: "$49,000",
      period: "/mes",
      description: "Para negocios en crecimiento",
      features: [
        "Hasta 50 facturas/mes",
        "Integraciones incluidas",
        "Soporte prioritario",
        "Reportes avanzados",
        "API access",
      ],
      cta: "Prueba Gratuita",
      popular: true,
    },
    {
      name: "Enterprise",
      price: "Personalizado",
      period: "",
      description: "Para grandes volúmenes",
      features: [
        "Facturas ilimitadas",
        "Soporte 24/7",
        "Integraciones personalizadas",
        "Gerente de cuenta dedicado",
        "SLA garantizado",
      ],
      cta: "Contactar Ventas",
      popular: false,
    },
  ]

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">FacturIA</span>
              <div className="hidden sm:flex items-center gap-1 ml-2">
                <div className="w-2 h-3 bg-yellow-400 rounded-sm"></div>
                <div className="w-2 h-3 bg-blue-500 rounded-sm"></div>
                <div className="w-2 h-3 bg-red-500 rounded-sm"></div>
              </div>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-8">
              <Link href="#inicio" className="text-gray-600 hover:text-gray-900 transition-colors">
                Inicio
              </Link>
              <Link href="#caracteristicas" className="text-gray-600 hover:text-gray-900 transition-colors">
                Características
              </Link>
              <Link href="#precios" className="text-gray-600 hover:text-gray-900 transition-colors">
                Precios
              </Link>
              <Link href="#contacto" className="text-gray-600 hover:text-gray-900 transition-colors">
                Contacto
              </Link>
            </nav>

            {/* CTA Buttons */}
            <div className="hidden md:flex items-center gap-3">
              <Link href="/login">
                <Button variant="outline" className="bg-transparent">
                  Iniciar Sesión
                </Button>
              </Link>
              <Link href="/dashboard">
                <Button className="bg-blue-600 hover:bg-blue-700">Prueba Gratuita</Button>
              </Link>
            </div>

            {/* Mobile Menu Button */}
            <button
              className="md:hidden p-2"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>

          {/* Mobile Menu */}
          {mobileMenuOpen && (
            <div className="md:hidden py-4 border-t border-gray-100">
              <div className="flex flex-col gap-4">
                <Link href="#inicio" className="text-gray-600 hover:text-gray-900 transition-colors">
                  Inicio
                </Link>
                <Link href="#caracteristicas" className="text-gray-600 hover:text-gray-900 transition-colors">
                  Características
                </Link>
                <Link href="#precios" className="text-gray-600 hover:text-gray-900 transition-colors">
                  Precios
                </Link>
                <Link href="#contacto" className="text-gray-600 hover:text-gray-900 transition-colors">
                  Contacto
                </Link>
                <div className="flex flex-col gap-2 pt-4 border-t border-gray-100">
                  <Link href="/login">
                    <Button variant="outline" className="w-full bg-transparent">
                      Iniciar Sesión
                    </Button>
                  </Link>
                  <Link href="/dashboard">
                    <Button className="w-full bg-blue-600 hover:bg-blue-700">Prueba Gratuita</Button>
                  </Link>
                </div>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <section id="inicio" className="relative bg-gradient-to-br from-blue-50 via-white to-green-50 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="space-y-4">
                <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100 w-fit">
                  🚀 Automatización para retail colombiano
                </Badge>
                <h1 className="text-4xl lg:text-5xl font-bold text-gray-900 leading-tight">
                  Automatiza el procesamiento de facturas para tu negocio retail
                </h1>
                <p className="text-xl text-gray-600 leading-relaxed">
                  IA + Visión por Computadora para extraer datos de facturas en segundos. Actualiza tu inventario
                  automáticamente.
                </p>
              </div>

              {/* Key Benefits */}
              <div className="flex flex-wrap gap-4">
                <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-full shadow-sm">
                  <Clock className="w-4 h-4 text-blue-600" />
                  <span className="text-sm font-medium">15 min → 2 min por factura</span>
                </div>
                <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-full shadow-sm">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm font-medium">+95% precisión</span>
                </div>
                <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-full shadow-sm">
                  <TrendingUp className="w-4 h-4 text-purple-600" />
                  <span className="text-sm font-medium">300%+ ROI</span>
                </div>
              </div>

              {/* CTA Buttons */}
              <div className="flex flex-col sm:flex-row gap-4">
                <Link href="/dashboard">
                  <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-lg px-8 py-3 w-full sm:w-auto">
                    Comenzar Prueba Gratuita
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Button>
                </Link>
                <Button size="lg" variant="outline" className="text-lg px-8 py-3 w-full sm:w-auto bg-transparent">
                  <Play className="w-5 h-5 mr-2" />
                  Ver Demo
                </Button>
              </div>
            </div>

            {/* Dashboard Mockup */}
            <div className="relative">
              <div className="bg-white rounded-2xl shadow-2xl p-6 transform rotate-2 hover:rotate-0 transition-transform duration-300">
                <div className="bg-gray-100 rounded-lg p-4 mb-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                    <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  </div>
                  <div className="space-y-3">
                    <div className="h-4 bg-blue-200 rounded w-3/4"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="h-16 bg-blue-100 rounded"></div>
                      <div className="h-16 bg-green-100 rounded"></div>
                      <div className="h-16 bg-purple-100 rounded"></div>
                    </div>
                    <div className="space-y-2">
                      <div className="h-2 bg-gray-200 rounded"></div>
                      <div className="h-2 bg-gray-200 rounded w-4/5"></div>
                      <div className="h-2 bg-gray-200 rounded w-3/5"></div>
                    </div>
                  </div>
                </div>
                <div className="text-center">
                  <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    Factura procesada exitosamente
                  </Badge>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Key Features */}
      <section id="caracteristicas" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
              Características que transforman tu negocio
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Tecnología de punta diseñada específicamente para el retail colombiano
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <Card key={index} className="border-0 shadow-lg hover:shadow-xl transition-shadow duration-300">
                <CardContent className="p-8 text-center">
                  <div
                    className={`w-16 h-16 ${feature.color} rounded-2xl flex items-center justify-center mx-auto mb-6`}
                  >
                    <feature.icon className="w-8 h-8" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-4">{feature.title}</h3>
                  <p className="text-gray-600 leading-relaxed">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Simple Process */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">Proceso simple en 3 pasos</h2>
            <p className="text-xl text-gray-600">De factura física a inventario actualizado en minutos</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {process.map((step, index) => (
              <div key={index} className="relative">
                <div className="text-center">
                  <div className="w-20 h-20 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-6">
                    <step.icon className="w-10 h-10 text-white" />
                  </div>
                  <div className="absolute -top-2 -left-2 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-sm font-bold text-blue-600">{step.step}</span>
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-3">{step.title}</h3>
                  <p className="text-gray-600">{step.description}</p>
                </div>
                {index < process.length - 1 && (
                  <div className="hidden md:block absolute top-10 left-full w-full">
                    <ArrowRight className="w-6 h-6 text-gray-300 mx-auto" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">Empresas que confían en FacturIA</h2>
            <p className="text-xl text-gray-600">
              Únete a cientos de retailers colombianos que ya automatizaron sus procesos
            </p>
          </div>

          {/* Client Logos */}
          <div className="flex flex-wrap justify-center items-center gap-8 mb-16 opacity-60">
            {["Almacén Medellín JA", "Melos Paisas", "Almacén El Rey", "Textiles Antioquia", "Calzado Colombia"].map(
              (company, index) => (
                <div key={index} className="bg-gray-100 px-6 py-3 rounded-lg">
                  <span className="font-semibold text-gray-700">{company}</span>
                </div>
              ),
            )}
          </div>

          {/* Testimonials */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <Card key={index} className="border-0 shadow-lg">
                <CardContent className="p-8">
                  <div className="flex items-center gap-1 mb-4">
                    {[...Array(testimonial.rating)].map((_, i) => (
                      <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />
                    ))}
                  </div>
                  <p className="text-gray-600 mb-6 italic">"{testimonial.text}"</p>
                  <div>
                    <p className="font-semibold text-gray-900">{testimonial.name}</p>
                    <p className="text-sm text-gray-500">{testimonial.company}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Preview */}
      <section id="precios" className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">Planes que se adaptan a tu negocio</h2>
            <p className="text-xl text-gray-600">Comienza gratis y escala según tus necesidades</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {pricing.map((plan, index) => (
              <Card
                key={index}
                className={`relative border-0 shadow-lg ${
                  plan.popular ? "ring-2 ring-blue-600 shadow-xl scale-105" : ""
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <Badge className="bg-blue-600 text-white hover:bg-blue-600">Más Popular</Badge>
                  </div>
                )}
                <CardContent className="p-8">
                  <div className="text-center mb-8">
                    <h3 className="text-xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                    <p className="text-gray-600 mb-4">{plan.description}</p>
                    <div className="mb-6">
                      <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
                      <span className="text-gray-600">{plan.period}</span>
                    </div>
                  </div>

                  <ul className="space-y-3 mb-8">
                    {plan.features.map((feature, featureIndex) => (
                      <li key={featureIndex} className="flex items-center gap-3">
                        <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
                        <span className="text-gray-600">{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    className={`w-full ${
                      plan.popular ? "bg-blue-600 hover:bg-blue-700" : "bg-gray-900 hover:bg-gray-800 text-white"
                    }`}
                  >
                    {plan.cta}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-blue-700">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">¿Listo para automatizar tu negocio?</h2>
          <p className="text-xl text-blue-100 mb-8">
            Únete a cientos de retailers colombianos que ya transformaron su operación
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/dashboard">
              <Button size="lg" className="bg-white text-blue-600 hover:bg-gray-100 text-lg px-8 py-3">
                Comenzar Prueba Gratuita
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
            <Button
              size="lg"
              variant="outline"
              className="border-white text-white hover:bg-white hover:text-blue-600 text-lg px-8 py-3 bg-transparent"
            >
              Hablar con Ventas
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer id="contacto" className="bg-gray-900 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {/* Company Info */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <FileText className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold">FacturIA</span>
              </div>
              <p className="text-gray-400">
                Automatización inteligente para el retail colombiano. Procesamiento de facturas con IA.
              </p>
              <div className="flex items-center gap-1">
                <div className="w-3 h-2 bg-yellow-400 rounded-sm"></div>
                <div className="w-3 h-2 bg-blue-500 rounded-sm"></div>
                <div className="w-3 h-2 bg-red-500 rounded-sm"></div>
                <span className="text-sm text-gray-400 ml-2">Hecho con ❤️ para el retail colombiano</span>
              </div>
            </div>

            {/* Product */}
            <div>
              <h4 className="font-semibold mb-4">Producto</h4>
              <ul className="space-y-2 text-gray-400">
                <li>
                  <Link href="#caracteristicas" className="hover:text-white transition-colors">
                    Características
                  </Link>
                </li>
                <li>
                  <Link href="#precios" className="hover:text-white transition-colors">
                    Precios
                  </Link>
                </li>
                <li>
                  <Link href="/dashboard" className="hover:text-white transition-colors">
                    Demo
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    API
                  </Link>
                </li>
              </ul>
            </div>

            {/* Support */}
            <div>
              <h4 className="font-semibold mb-4">Soporte</h4>
              <ul className="space-y-2 text-gray-400">
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Centro de Ayuda
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Documentación
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Términos de Servicio
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Política de Privacidad
                  </Link>
                </li>
              </ul>
            </div>

            {/* Contact */}
            <div>
              <h4 className="font-semibold mb-4">Contacto</h4>
              <ul className="space-y-3 text-gray-400">
                <li className="flex items-center gap-2">
                  <Mail className="w-4 h-4" />
                  <a href="mailto:info@facturia.co" className="hover:text-white transition-colors">
                    info@facturia.co
                  </a>
                </li>
                <li className="flex items-center gap-2">
                  <Phone className="w-4 h-4" />
                  <a href="tel:+573001234567" className="hover:text-white transition-colors">
                    +57 300 123 4567
                  </a>
                </li>
                <li className="flex items-center gap-2">
                  <MapPin className="w-4 h-4" />
                  <span>Medellín, Colombia</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-800 mt-12 pt-8 text-center text-gray-400">
            <p>&copy; 2024 FacturIA. Todos los derechos reservados.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
