package hello

object HelloWorldTest {

  def main(args: Array[String]) {
    
    var points = 0
    
    try {
      
	    println("Constructing HelloWorld:")
	    val hello = new HelloWorld
	    println(">>> " + hello)
	    points += 1
	    
	    println("Calling hello method:")
	    val str = hello.hello
	    println(">>> " + str)
	    points += 1
	    
	    if (str == "Hello world!") {
	      println("Correct value!")
	      points += 2
	    }
	    else {
	      println("Incorrect value!")
	    }
	
    } finally {
      println("TotalPoints: " + points)
      println("MaxPoints: 4")
    }
  }
}
