package hello

object HelloScalaTest {

  def main(args: Array[String]) {

    var points = 0
    var max_points = 4

    try {

	    println("Calling HelloScala.hello method:")
	    val str = HelloScala.hello
	    println(">>> " + str)
	    points += 1

	    if (str == "Hello Scala!") {
	      println("Correct value!")
	      points += 3
	    }
	    else {
	      println("Incorrect value!")
	    }

    } finally {
      println("TotalPoints: " + points)
      println("MaxPoints: " + max_points)
    }
  }
}
